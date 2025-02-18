#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import os
import torch.distributed as dist

from colossalai.context import Config
from colossalai.registry import DIST_GROUP_INITIALIZER
from .process_group_initializer import ProcessGroupInitializer
from ..parallel_mode import ParallelMode
from colossalai.constants import PARALLEL_INPUT_1D


@DIST_GROUP_INITIALIZER.register_module
class Initializer_1D(ProcessGroupInitializer):
    """A ProcessGroupInitializer for 1d tensor parallelism.

    :param args: Args used to initialize ProcessGroupInitializer
    :param kwargs: Kwargs used to initialize ProcessGroupInitializer
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_group = self.world_size // self.tensor_parallel_size

    def init_dist_group(self):
        """Initialize 1D tensor parallel groups, and assign local_ranks and groups to each gpu.

        :return: (local_rank, group_world_size, process_group, ranks_in_group, mode)
        :rtype: Tuple
        """
        local_rank = None
        ranks_in_group = None
        process_group = None
        group_world_size = None
        mode = ParallelMode.PARALLEL_1D
        os.environ[PARALLEL_INPUT_1D] = ''

        for i in range(self.num_group):
            ranks = [i * self.tensor_parallel_size + j for j in range(self.tensor_parallel_size)]
            group = dist.new_group(ranks)

            if self.rank in ranks:
                local_rank = ranks.index(self.rank)
                group_world_size = len(ranks)
                process_group = group
                ranks_in_group = ranks

        return local_rank, group_world_size, process_group, ranks_in_group, mode
