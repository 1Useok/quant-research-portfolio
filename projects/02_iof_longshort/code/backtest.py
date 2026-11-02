"""시가 체결, 슬리브별 보유 수량과 종목별 순잔고를 연결하는 현금 장부."""

from collections import defaultdict

from signals import select

INITIAL_CASH = 100_000.0
SLEEVES = 5
TRADE_RATE = 10 / 10_000
BORROW_PER_SESSION = 0.0252 / 252


def net_shares(books):
    net = defaultdict(float)
    for book in books:
        for symbol, qty in book.items():
            net[symbol] += qty
    return net


def current_sides(book):
    return {"long": next((s for s, q in book.items() if q > 0), None),
            "short": next((s for s, q in book.items() if q < 0), None)}


def refresh(books, index, held, targets, auction, budget):
    book, orders = books[index], []

    def order(side, symbol, action, target_value, locked=False):
        price = auction.prices.get(symbol)
        before = book.get(symbol, 0.0)
        filled = 0.0
        if locked:
            status = "slot_locked"
        elif price is None:
            status = "no_open"
        else:
            target_qty = target_value / price
            filled = target_qty - before
            status = "filled" if filled else "at_target"
            if filled < 0 and symbol not in auction.borrowable:
                # 대차 없이 팔 수 있는 수량은 계좌의 기존 순롱 잔고까지다.
                sellable = max(0.0, net_shares(books).get(symbol, 0.0))
                if -filled > sellable:
                    filled = -sellable
                    target_qty = before + filled
                    status = "partial_locate" if filled else "no_locate"
            if target_qty:
                book[symbol] = target_qty
            else:
                book.pop(symbol, None)
        orders.append(dict(side=side, symbol=symbol, action=action, status=status,
                           target_value=target_value, open=price, qty_before=before,
                           filled_qty=filled, qty_after=book.get(symbol, 0.0)))

    for side, sign in (("long", 1), ("short", -1)):
        old, pick = held[side], targets[side]
        if old is not None and old != pick:
            order(side, old, "exit", 0.0)
        if pick is not None:
            locked = old != pick and old in book
            order(side, pick, "resize" if old == pick else "enter", sign * budget, locked)
    return orders


def simulate(means, closes, auctions):
    days = sorted(closes)
    if len(days) < 3:
        raise ValueError("신호·체결·평가에 최소 세 거래일이 필요합니다.")
    result = {name: [] for name in ("signals", "orders", "holdings", "daily")}
    books = [{} for _ in range(SLEEVES)]
    cash, marks = INITIAL_CASH, {}

    for turn, (signal, entry, end) in enumerate(zip(days, days[1:], days[2:])):
        index = turn % SLEEVES
        context = dict(signal_date=signal, entry_date=entry, sleeve=index + 1)
        held = current_sides(books[index])
        targets, audit = select(signal, closes[signal], means, held)
        result["signals"].extend({**context, **row} for row in audit)

        auction = auctions[entry]
        marks.update(auction.prices)
        before = net_shares(books)
        cash_before = cash
        nav_start = cash + sum(q * marks[s] for s, q in before.items())
        if nav_start <= 0:
            raise ValueError("갱신 전 NAV가 양수여야 합니다.")
        orders = refresh(books, index, held, targets, auction, nav_start * 0.5 / SLEEVES)
        result["orders"].extend({**context, **row} for row in orders)

        after = net_shares(books)
        trades = []
        for s in sorted(before.keys() | after.keys()):
            delta = after.get(s, 0.0) - before.get(s, 0.0)
            if delta:
                trades.append(delta * auction.prices[s])
        traded = sum(abs(v) for v in trades)
        trade_cost = traded * TRADE_RATE
        long_value = sum(q * marks[s] for s, q in after.items() if q > 0)
        short_value = sum(-q * marks[s] for s, q in after.items() if q < 0)
        borrow_fee = short_value * BORROW_PER_SESSION
        cash -= sum(trades) + trade_cost + borrow_fee

        next_prices = auctions[end].prices
        end_marks = marks | next_prices
        gross_pnl = sum(q * (end_marks[s] - marks[s]) for s, q in after.items())
        nav_end = cash + sum(q * end_marks[s] for s, q in after.items())
        for sleeve, book in enumerate(books, 1):
            for s, qty in sorted(book.items()):
                position = dict(
                    entry_date=entry, mark_date=end, sleeve=sleeve, symbol=s, qty=qty,
                    entry_mark=marks[s], end_mark=end_marks[s], entry_stale=int(s not in auction.prices),
                    end_stale=int(s not in next_prices),
                )
                result["holdings"].append(position)
        net_pnl = nav_end - nav_start
        interval = dict(
            **context, mark_date=end, cash_before=cash_before, nav_start=nav_start,
            traded=traded, turnover=traded / nav_start,
            trade_cost=trade_cost, long_value=long_value, short_value=short_value,
            borrow_fee=borrow_fee, gross_pnl=gross_pnl, net_pnl=net_pnl,
            cash_after=cash, nav_end=nav_end, net_return=net_pnl / nav_start,
        )
        result["daily"].append(interval)
    return result
