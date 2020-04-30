"""Data loader for CIFAR data with ensemble predictions"""
import logging
import h5py
import torch
import torchvision
import torchvision.transforms as transforms
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image


class Cifar10Data:
    """CIFAR data wrapper with ensemble predictions,
    data is organized as ((img, ensemble preds, ensemble logits), labels)
    """

    def __init__(self, ind=None, train=True, augmentation=False, corrupted=False,
                 data_dir="../../dataloaders/data/ensemble_predictions/"):
        self._log = logging.getLogger(self.__class__.__name__)

        if augmentation:
            self.transform = transforms.Compose([
                transforms.RandomCrop(32, padding=4),
                transforms.RandomHorizontalFlip(),
                transforms.ToTensor()])
        else:
            self.transform = transforms.ToTensor()

        filepath = data_dir + "ensemble_predictions.h5"

        with h5py.File(filepath, 'r') as f:
            if train:
                data_grp = f["train"]
            else:
                data_grp = f["test"]

            data = data_grp["data"][()]
            predictions = data_grp["predictions"][()]
            logits = data_grp["logits"][()]
            targets = data_grp["targets"][()]

        if ind is None:
            data = (data, predictions, logits)
            targets = targets

        else:
            data = (data[ind, :, :, :], predictions[ind, :, :], logits[ind, :, :])
            targets = targets[ind]

        if corrupted:
            training_inds = np.load(data_dir + "corrupted_data_indices.npy")[:5000]

            corrupted_data = []
            corrupted_predictions = []
            corrupted_logits = []
            corrupted_targets = []
            corruptions = ["contrast", "frost", "gaussian_blur", "impulse_noise"]

            filepath = data_dir + "ensemble_predictions_corrupted_data.h5"
            with h5py.File(filepath, 'r') as f:

                for corruption in corruptions:
                    grp = f[corruption]

                    for i in (1, 2):
                        sub_grp = grp["intensity_" + str(i)]

                        corrupted_data.append(sub_grp["data"][()][training_inds, :, :, :] * 255)
                        corrupted_predictions.append(sub_grp["predictions"][()][training_inds, :, :])
                        corrupted_logits.append(sub_grp["logits"][()][training_inds, :, :])
                        corrupted_targets.append(sub_grp["targets"][()][training_inds])

            data[0] = np.concatenate((data[0], np.concatenate(corrupted_data, axis=0)), axis=0)
            data[1] = np.concatenate((data[1], np.concatenate(corrupted_predictions, axis=0)), axis=0)
            data[2] = np.concatenate((data[2], np.concatenate(corrupted_logits, axis=0)), axis=0)
            targets = np.concatenate((np.concatenate(corrupted_targets, axis=0)), axis=0)

        self.set = CustomSet(data[0], data[1], data[2], targets, self.transform)

        ensemble_predictions = np.argmax(np.mean(self.set.data[1], axis=1), axis=-1)
        acc = np.mean(ensemble_predictions == np.squeeze(self.set.targets))
        print("Ensemble accuracy: {}".format(acc))

        self.classes = ("plane", "car", "bird", "cat", "deer", "dog", "frog",
                        "horse", "ship", "truck")
        self.num_classes = len(self.classes)


class CustomSet():

    def __init__(self, img, predictions, logits, targets, transform):
        self.data = (img, predictions, logits)
        self.targets = targets
        self.transform = transform

        self.input_size = self.data[0].shape[0]

    def __len__(self):
        return self.input_size

    def __getitem__(self, index):
        """
        Args:
            index (int): Index

        Returns:
            tuple: (image, ensemble_preds, ensemble_logits, target) where target is index of the target class.
        """
        img, preds, logits = self.data[0], self.data[1], self.data[2]
        img, preds, logits, target = img[index], preds[index], logits[index], self.targets[index]

        # doing this so that it is consistent with all other datasets
        # to return a PIL Image

        img = Image.fromarray(img)

        if self.transform is not None:
            img = self.transform(img)

        preds = torch.tensor(preds)
        logits = torch.tensor(logits)
        target = torch.tensor(target)

        return (img, preds, logits), target



def main():
    """Entry point for debug visualisation"""
    # get some random training images
    data = Cifar10Data(data_dir="data/ensemble_predictions/")
    loader = torch.utils.data.DataLoader(data.set,
                                         batch_size=4,
                                         shuffle=True,
                                         num_workers=0)
    dataiter = iter(loader)
    inputs, labels = dataiter.next()

    img = inputs[0]
    probs = inputs[1].data.numpy()
    preds = np.argmax(np.mean(probs, axis=1), axis=-1)

    acc = np.mean(preds == labels.data.numpy())
    print("Accuracy is {}".format(acc))

    # show images
    imshow(torchvision.utils.make_grid(img))
    # print labels
    print(" ".join("%5s" % data.classes[labels[j]] for j in range(4)))


def imshow(img):
    """Imshow helper
    TODO: Move to utils
    """
    npimg = img.numpy()
    plt.imshow(np.transpose(npimg, (1, 2, 0)))
    plt.show()


if __name__ == "__main__":
    main()
