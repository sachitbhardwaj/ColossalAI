#!/usr/bin/env python
# -*- encoding: utf-8 -*-


from typing import List
from torch.nn import Module
from torch.nn.modules.loss import _Loss
from torch.optim import Optimizer

from colossalai.logging import get_dist_logger
from torch import Tensor


class Engine:
    """Basic engine class for training and evaluation. It runs a specific process method 
    :meth:`step` which is based on the given :attr:`schedule` over each batch of a dataset.
    It controls a iteration in training.

    :param model: The neural network model
    :type model: ``torch.nn.Module``
    :param optimizer: Optimizer for updating the parameters
    :type optimizer: ``torch.optim.Optimizer``
    :param criterion: Loss function for calculating loss
    :type criterion: ``torch.nn.modules.loss._Loss``
    :param gradient_handlers: A list of gradient handler used in backward
    :type gradient_handlers: list
    :param clip_grad_norm: The norm of gradient clipping
    :type clip_grad_norm: float, optional
    :param verbose: whether to display log info
    :type verbose: bool
    """

    def __init__(self,
                 model: Module,
                 optimizer: Optimizer,
                 criterion: _Loss,
                 gradient_handlers: List = None,
                 clip_grad_norm: float = 0.0,
                 verbose: bool = True
                 ):
        self._model = model
        self._optimizer = optimizer
        self._criterion = criterion
        self._clip_grad_norm = clip_grad_norm
        self._verbose = verbose
        self._logger = get_dist_logger()

        # state
        self.training = True  # default

        # build gradient handler
        if gradient_handlers:
            self._gradient_handlers = gradient_handlers
        else:
            self._gradient_handlers = []

    @property
    def model(self):
        """Model attached to the engine"""
        return self._model

    @property
    def optimizer(self):
        """Optimizer attached to the engine"""
        return self._optimizer

    @property
    def criterion(self):
        """Criterion attached to the engine"""
        return self._criterion

    def zero_grad(self):
        """Set the gradient of parameters to zero
        """
        self.optimizer.zero_grad()

    def step(self):
        """Execute parameter update
        """
        self._all_reduce_gradients()
        self.optimizer.clip_grad_norm(self.model, self._clip_grad_norm)
        return self.optimizer.step()

    def backward(self, loss: Tensor):
        """Start backward propagation given the loss value computed by a loss function

        :param loss: Loss value computed by a loss function
        :type loss: :class:`torch.Tensor`
        """
        return self.optimizer.backward(loss)

    def backward_by_grad(self, tensor, grad):
        """Start backward propagation given the gradient of the output tensor

        :param tensor: Output tensor
        :type tensor: :class:`torch.Tensor`
        :param grad: Gradient passed back to the output
        :type grad: :class:`torch.Tensor`
        """
        return self.optimizer.backward_by_grad(tensor, grad)

    def calc_loss(self, *args, **kwargs):
        """Compute the loss value

        :param args: Args used in criterion function
        :param kwargs: Kwargs used in criterion function

        :return: The loss value
        :rtype: :class:`torch.Tensor`
        """
        return self.criterion(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        """Run the forward step for the model

        :return: Output the model
        :rtype: Tuple[:class:`torch.Tensor`] or :class:`torch.Tensor`
        """
        return self.model(*args, **kwargs)

    def _all_reduce_gradients(self):
        """Handles all-reduce operations of gradients across different parallel groups.
        """
        for handler in self._gradient_handlers:
            handler.handle_gradient()

    def train(self):
        """Sets the model to training mode.
        """
        self.training = True
        self._model.train()

    def eval(self):
        """Sets the model to evaluation mode.
        """
        self.training = False
        self._model.eval()
