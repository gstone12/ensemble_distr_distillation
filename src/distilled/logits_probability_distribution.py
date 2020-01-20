import torch
import torch.nn as nn
import torch.optim as torch_optim
import src.loss as custom_loss
import src.distilled.distilled_network as distilled_network


class LogitsProbabilityDistribution(distilled_network.DistilledNet):
    def __init__(self,
                 layer_sizes,
                 teacher,
                 device=torch.device('cpu'),
                 use_hard_labels=False,
                 learning_rate=0.001,
                 scale_teacher_logits=False):

        super().__init__(teacher=teacher,
                         loss_function=custom_loss.gaussian_neg_log_likelihood,
                         device=device)

        self.use_hard_labels = use_hard_labels
        self.learning_rate = learning_rate
        self.scale_teacher_logits = scale_teacher_logits

        self.layers = nn.ModuleList()
        for i in range(len(layer_sizes) - 1):
            self.layers.append(nn.Linear(layer_sizes[i], layer_sizes[i + 1]))

        # Ad-hoc fix zero variance.
        self.variance_lower_bound = 0.001
        if self.variance_lower_bound > 0.0:
            self._log.warning("Non-zero variance lower bound set ({})".format(
                self.variance_lower_bound))

        self.optimizer = torch_optim.Adam(self.parameters(),
                                          lr=self.learning_rate)

        self.to(self.device)

    def forward(self, x):
        """Estimate parameters of distribution
        """

        for layer in self.layers[:-1]:
            x = nn.functional.relu(layer(x))

        x = self.layers[-1](x)

        mid = int(x.shape[-1] / 2)
        mean = x[:, :mid]
        var_z = x[:, mid:]

        var = torch.log(1 + torch.exp(var_z)) + self.variance_lower_bound
        #var = torch.exp(var_z)

        return mean, var

    def _generate_teacher_predictions(self, inputs):
        """Generate teacher predictions"""

        logits = self.teacher.get_logits(inputs)

        if self.scale_teacher_logits:
            scaled_logits = logits - torch.stack([logits[:, :, -1]], axis=-1)
            logits = scaled_logits[:, :, :-1]

        return logits

    def predict(self, input_, num_samples=None):
        """Predict parameters
        Wrapper function for the forward function.
        """

        if num_samples is None:
            num_samples = 50

        mean, var = self.forward(input_)

        samples = torch.zeros(
            [input_.size(0), num_samples,
             int(self.output_size / 2)])
        for i in range(input_.size(0)):

            rv = torch.distributions.multivariate_normal.MultivariateNormal(
                loc=mean[i, :], covariance_matrix=torch.diag(var[i, :]))

            samples[i, :, :] = rv.rsample([num_samples])

        softmax_samples = torch.exp(samples) / (
            torch.sum(torch.exp(samples), dim=-1, keepdim=True) + 1)

        return softmax_samples

    def predict_logits(self, input_, num_samples=None):
        """Predict parameters
        Wrapper function for the forward function.
        """

        if num_samples is None:
            num_samples = 50

        mean, var = self.forward(input_)

        samples = torch.zeros(
            [input_.size(0), num_samples,
             int(self.output_size / 2)])
        for i in range(input_.size(0)):

            rv = torch.distributions.multivariate_normal.MultivariateNormal(
                loc=mean[i, :], covariance_matrix=torch.diag(var[i, :]))

            samples[i, :, :] = rv.rsample([num_samples])

        return samples

    def _learning_rate_condition(self, epoch=None):
        """Evaluate condition for increasing learning rate
        Defaults to never increasing. I.e. returns False
        """

        return True

    def calculate_loss(self, outputs, teacher_predictions, labels=None):
        """Calculate loss function
        Wrapper function for the loss function.
        """

        return self.loss(outputs, teacher_predictions)

    # TÄNKER MIG ATT VI KAN HA EN CALC_REG

    def mean_expected_value(self, outputs, teacher_predictions):
        exp_value = outputs[0]

        return torch.mean(exp_value, dim=0)

    def mean_variance(self, outputs, teacher_predictions):
        variance = outputs[1]

        return torch.mean(variance, dim=0)
