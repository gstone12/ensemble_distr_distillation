"""One dimensional dataset,
Gaussian with sinus wave mean, variance increasing in x

Taken from paper: "https://arxiv.org/abs/1906.01620"
"""
from pathlib import Path
import csv
import numpy as np
import torch.utils.data
import matplotlib.pyplot as plt
import logging


class GaussianSinus(torch.utils.data.Dataset):
    def __init__(self,
                 store_file,
                 train=True,
                 reuse_data=False,
                 n_samples=1000):

        super(GaussianSinus).__init__()
        self._log = logging.getLogger(self.__class__.__name__)
        self.n_samples = n_samples
        self.train = train

        self.file = Path(store_file)
        if self.file.exists() and reuse_data:
            self.validate_dataset()
        else:
            self._log.info("Sampling new data")
            self.sample_new_data()

    def __len__(self):
        return self.n_samples

    def __getitem__(self, index):
        sample = None
        with self.file.open(newline="") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",", quotechar="|")
            for count, row in enumerate(csv_reader):
                if count == index:
                    sample = row
                    break
        inputs = sample[:-1]
        targets = sample[-1]

        return (np.array(inputs, dtype=np.float32),
                np.array([targets], dtype=np.float32))

    def sample_new_data(self):
        self.file.parent.mkdir(parents=True, exist_ok=True)
        if self.train:
            x = np.random.uniform(low=-3.0, high=3.0, size=self.n_samples)
            mu = np.sin(x)
            sigma = 0.15 * 1 / (1 + np.exp(-x))
            sigma **= 2
            y = np.random.multivariate_normal(mean=mu, cov=(np.diag(sigma)))

        else:
            x = np.random.uniform(low=-3.0, high=3.0, size=self.n_samples)

        combined_data = np.column_stack((x, y))
        np.random.shuffle(combined_data)
        np.savetxt(self.file, combined_data, delimiter=",")

    def validate_dataset(self):
        with self.file.open(newline="") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",", quotechar="|")
            assert self.n_samples - 1 == sum(1 for row in csv_reader)

    def get_full_data(self):
        tmp_raw_data = list()
        with self.file.open(newline="") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",", quotechar="|")
            tmp_raw_data = [data for data in csv_reader]
        return np.array(tmp_raw_data, dtype=float)


def plot_reg_data(data, ax):
    inputs = data[:, :-1]
    targets = data[:, -1]
    ax.scatter(inputs, targets)
    plt.show()


def main():
    _, ax = plt.subplots()
    dataset = GaussianSinus(store_file=Path("data/1d_gauss_sinus_1000"))
    plot_reg_data(dataset.get_full_data(), ax)


if __name__ == "__main__":
    main()
