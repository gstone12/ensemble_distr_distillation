import numpy as np
import torch
import torchvision
import logging
from matplotlib import pyplot as plt
from pathlib import Path
from datetime import datetime
from src.distilled import dirichlet_probability_distribution
from src.ensemble import ensemble
import src.metrics as metrics
import src.utils as utils
from src.dataloaders import mnist
from src.ensemble import simple_classifier
import src.utils as utils

LOGGER = logging.getLogger(__name__)


def create_ensemble(train_loader, valid_loader, test_loader, args, num_ensemble_members,
                    filepath):
    """Create an ensemble model"""

    input_size = 784
    hidden_size_1 = 54
    hidden_size_2 = 32
    output_size = 10

    prob_ensemble = ensemble.Ensemble(output_size)

    for i in range(num_ensemble_members):
        LOGGER.info("Training ensemble member number {}".format(i + 1))
        member = simple_classifier.SimpleClassifier(input_size,
                                                    hidden_size_1,
                                                    hidden_size_2,
                                                    output_size,
                                                    learning_rate=args.lr)

        prob_ensemble.add_member(member)

    acc_metric = metrics.Metric(name="Acc", function=metrics.accuracy)
    prob_ensemble.add_metrics([acc_metric])
    prob_ensemble.train(train_loader, args.num_epochs, valid_loader)
    LOGGER.info("Ensemble accuracy on test data: {}".format(
        get_accuracy(prob_ensemble, test_loader)))

    prob_ensemble.save_ensemble(filepath)

    return prob_ensemble


def uncertainty_rotation(model, test_sample, ax):
    """Get uncertainty separation for model on rotated data set"""

    test_img = test_sample[0][0].view(28, 28)
    test_label = test_sample[1][0]

    num_points = 10
    max_val = 90
    angles = torch.arange(-max_val, max_val, max_val * 2 / num_points)

    rotated_data_set = generate_rotated_data_set(test_img, angles)
    plot_data_set(rotated_data_set)

    rotated_data_set = torch.stack(
        [data_point.view(28 * 28) for data_point in rotated_data_set])

    predicted_distribution = model.predict(rotated_data_set)
    tot_unc, ep_unc, al_unc = metrics.uncertainty_separation_entropy(predicted_distribution, None)

    LOGGER.info("True label is: {}".format(test_label))
    LOGGER.info("Model prediction: {}".format(np.argmax(predicted_distribution, axis=-1)))

    angles = angles.data.numpy()
    ax.plot(angles, tot_unc.data.numpy(), 'o--')
    ax.plot(angles, ep_unc.data.numpy(), 'o--')
    ax.plot(angles, al_unc.data.numpy(), 'o--')
    ax.set_xlabel('Rotation angle')
    ax.set_ylabel('Uncertainty')
    ax.legend(["Total", "Epistemic", "Aleatoric"])


def generate_rotated_data_set(img, angles):
    """Generate a set of rotated images from a single image
    Args:
        img (tensor(dim=2)): image to be rotated
        angles (tensor/ndarray): set of angles for which the image should be rotated
    """
    img = torchvision.transforms.ToPILImage()(img)
    data_set = [
        torch.squeeze(torchvision.transforms.ToTensor()(
            torchvision.transforms.functional.rotate(img, angle=angle)))
        for angle in angles
    ]

    return data_set


def get_accuracy(model, data_loader):
    """Calculate accuracy of model on data in dataloader"""

    accuracy = 0
    num_batches = 0
    for batch in data_loader:
        inputs, labels = batch
        predicted_distribution = model.predict(inputs)
        accuracy += metrics.accuracy(labels, predicted_distribution)
        num_batches += 1

    return accuracy / num_batches


def plot_data_set(data_set):
    """Plot of image data set
    Args:
        data_set (list(len=10)): list of ten images/2D ndarrays
    """

    # TODO: Make loop instead
    fig, axes = plt.subplots(2, 5)
    axes[0, 0].imshow(data_set[0])
    axes[0, 1].imshow(data_set[1])
    axes[0, 2].imshow(data_set[2])
    axes[0, 3].imshow(data_set[3])
    axes[0, 4].imshow(data_set[4])
    axes[1, 0].imshow(data_set[5])
    axes[1, 1].imshow(data_set[6])
    axes[1, 2].imshow(data_set[7])
    axes[1, 3].imshow(data_set[8])
    axes[1, 4].imshow(data_set[9])

    plt.setp(plt.gcf().get_axes(), xticks=[], yticks=[])
    plt.show()


def main():
    """Main"""

    args = utils.parse_args()

    log_file = Path("{}.log".format(datetime.now().strftime('%Y%m%d_%H%M%S')))
    utils.setup_logger(log_path=Path.cwd() / args.log_dir / log_file,
                       log_level=args.log_level)

    train_set = mnist.MnistData()
    valid_set = mnist.MnistData(data_set='validation')
    test_set = mnist.MnistData(train=False)

    train_loader = torch.utils.data.DataLoader(train_set,
                                               batch_size=32,
                                               shuffle=True,
                                               num_workers=0)

    valid_loader = torch.utils.data.DataLoader(valid_set,
                                               batch_size=32,
                                               shuffle=True,
                                               num_workers=0)

    test_loader = torch.utils.data.DataLoader(test_set,
                                              batch_size=32,
                                              shuffle=True,
                                              num_workers=0)

    num_ensemble_members = 5

    ensemble_filepath = Path("models/mnist_ensemble_5")

    prob_ensemble = create_ensemble(train_loader, valid_loader, test_loader,
                                    args, num_ensemble_members, ensemble_filepath)

    # prob_ensemble = ensemble.Ensemble()
    # prob_ensemble.load_ensemble(ensemble_filepath)
    # LOGGER.info("Ensemble accuracy on test data: {}".format(
    #     get_accuracy(prob_ensemble, test_loader)))

    # TODO: get specific sample
    test_sample = next(iter(test_loader))
    fig, ax = plt.subplots(1,2)
    uncertainty_rotation(prob_ensemble, test_sample, ax[0])
    uncertainty_rotation(prob_ensemble.members[0], test_sample, ax[1])
    plt.show()


if __name__ == "__main__":
    main()