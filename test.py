import threading
import time


def my_function():
    # Do something in the thread
    time.sleep(2)
    print(1)

my_thread = threading.Thread(target=my_function)
my_thread.start()

for i in range(1, 5):
    time.sleep(2)
    if my_thread.is_alive():
        print("Thread is still running")
    else:
        print("Thread has finished")