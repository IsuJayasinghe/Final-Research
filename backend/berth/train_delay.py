"""
Bridge script to run Delay Risk model training from the backend root folder.
"""
from app.ml.train_delay import train_and_save_delay_model

if __name__ == "__main__":
    train_and_save_delay_model()
