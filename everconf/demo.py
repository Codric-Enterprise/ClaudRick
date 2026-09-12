"""
everconf in 30 seconds.

Run this file. That's the whole demo:

    python demo.py

One label in a small dataset was never actually measured — someone
filled the gap with a plausible guess, the way a real pipeline does
every day. Watch what each library does with that.
"""

from sklearn.metrics import mean_squared_error
from everconf import C, UNKNOWN, mse

y_true      = [3.0, 5.0, 2.0, 8.0]   # the 3rd label was never measured —
y_true_real = [3.0, 5.0, None, 8.0]  # this is what's actually true
y_pred      = [2.9, 5.1, 2.0, 7.8]

print("y_true (a guess silently filled the missing 3rd label):", y_true)
print("y_pred:                                                ", y_pred)
print()

sklearn_result = mean_squared_error(y_true, y_pred)
print(f"sklearn.metrics.mean_squared_error(y_true, y_pred) = {sklearn_result}")
print("   -> clean, confident, and WRONG. It has no idea one input was a guess.")
print()

ec_true = [C(v) if v is not None else UNKNOWN for v in y_true_real]
ec_pred = [C(v) for v in y_pred]
ec_result = mse(ec_true, ec_pred)
print(f"everconf.mse(y_true, y_pred)                       = {ec_result}")
print("   -> UNKNOWN. The missing label poisons the score instead of hiding in it.")
print()

print("That's the entire idea: a number that refuses to average over")
print("data that was never measured. pandas skips it. sklearn skips it.")
print("everconf can't — refusing is the whole point.")
