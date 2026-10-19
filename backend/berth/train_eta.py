"""
Bridge script to run ETA model training from the backend root folder.
"""
from app.ml.train_eta import train_and_save_model

if __name__ == "__main__":
    train_and_save_model()
