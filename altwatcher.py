#!/usr/bin/env python
# NOTE: Python 3 6 is required
import curses, datetime, coinmarketcap, pickle, sys, threading, time, traceback
from collections import defaultdict

cmc = coinmarketcap.Market()
histories = defaultdict(list)  # A map of form: "CUR1/CUR2": [CONVERSION...]
histfile = "/tmp/cmchistory.pickle"
last, updated = datetime.datetime.now(), []

pairs = (
    "bitcoin/ethereum",
    "bitcoin/litecoin",
    "ethereum/litecoin",
    "nano/decred",
)

def tick(c1, c2):
    ct1 = cmc.ticker(c1)[0]
    ct2 = cmc.ticker(c2)[0]
    forward = float(ct1["price_usd"]) / float(ct2["price_usd"])
    timestamp = datetime.datetime.fromtimestamp(int(ct1["last_updated"]))
    ticker = f"{c1}/{c2}"
    # Only add changed values.
    try:
        if str(forward) == str(histories[ticker][-1][1]):
            return
    except IndexError:
        pass
    global updated
    updated.append(ticker)
    histories[ticker].append((timestamp, forward))

def do_tick(event):
    sleeptime = 30
    sleep = 0
    while not event.wait(1):
        # Loop with a more fine-grained interrupt schedule.
        if sleep > 0:
            sleep -= 1
            time.sleep(1)
            continue
        sleep = sleeptime
        # Update the price histories.
        last = datetime.datetime.now()
        try:
            for pair in pairs:
                tick(*pair.split("/"))
        except:
            # Don't spit out errors.
            pass


# GUI Rendering.
def render_boxes(screen, my, mx, reverse):
    pair_count = len(pairs)
    box_height = my // pair_count

    for i, pair in enumerate(pairs):
        ystart = box_height * i
        win = curses.newwin(box_height, mx, ystart, 0)
        win.addstr(0, 0, "-" * mx)
        win.addstr(1, 0, pair.center(mx))
        try:
            prices = [1 / h[1] if reverse else h[1]
                      for h in histories[pair]]
            data = (" " * 4).join([
                f"{min(prices)}",
                f"{sum(prices) / len(prices)}",
                f"{max(prices)}",
            ]).center(mx)
            prices = [h[1] if reverse else 1 / h[1]
                      for h in histories[pair]]
            rdata = (" " * 4).join([
                f"{max(prices)}",
                f"{sum(prices) / len(prices)}",
                f"{min(prices)}",
            ]).center(mx)
            if pair in updated:
                win.addstr(2, 0, data, curses.A_BOLD)
                win.addstr(3, 0, rdata, curses.A_BOLD)
            else:
                win.addstr(2, 0, data)
                win.addstr(3, 0, rdata)
        except (IndexError, ValueError):
            pass
        win.addstr(4, 0, "-" * mx)

        first_row = 5
        for i in range(first_row, box_height):
            try:
                timestamp, forward = histories[pair][-(i - (first_row - 1))]

                data = (" " * 4).join([
                    f"{timestamp}",
                    f"{forward}",
                    f"{1 / forward}",
                ]).center(mx - 1)
                if pair in updated and i == first_row:
                    win.addstr(i, 0, data, curses.A_BOLD)
                else:
                    win.addstr(i, 0, data)
            except IndexError:
                break

        win.refresh()

def main(screen):
    screen.nodelay(True)
    reverse = True
    while True:
        key = screen.getch()
        if key == ord("r"):
            reverse = not reverse
        elif key == ord("q"):
            break
        render_boxes(screen, *screen.getmaxyx(), reverse)
        updated.clear()
        screen.refresh()
        time.sleep(1)


if __name__ == "__main__":
    print("Loading Data")
    try:
        with open(histfile, "rb") as cmchistory:
            histories = pickle.load(cmchistory)
    except:
        print("Failed to Load Data")

    event = threading.Event()
    thr = threading.Thread(target=do_tick, args=(event,))
    thr.start()

    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        event.set()
    thr.join()

    print("Saving Data")
    with open(histfile, "wb") as cmchistory:
        pickle.dump(histories, cmchistory)
