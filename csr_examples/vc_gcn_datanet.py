# Copyright 2022 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""gcn model implemented using mindspore-gl"""
import time
import argparse

import numpy as np
import mindspore as ms
from mindspore.profiler import Profiler
import mindspore.nn as nn
import mindspore.ops as ops
import mindspore.context as context

from gnngraph_dataset import GraphDataset
from gcn import GCNNet


class LossNet(nn.Cell):
    """ LossNet definition """

    def __init__(self, net):
        super().__init__()
        self.net = net
        self.loss_fn = nn.loss.SoftmaxCrossEntropyWithLogits(sparse=True, reduction='none')

    def construct(self, x, in_deg, out_deg, train_mask, target, n_nodes, indptr, indices):
        predict = self.net(x, in_deg, out_deg, n_nodes, indptr, indices)
        target = ops.Squeeze()(target)
        loss = self.loss_fn(predict, target)
        loss = loss * train_mask
        return ms.ops.ReduceSum()(loss) / ms.ops.ReduceSum()(train_mask)


class DataNet(ms.nn.Cell):
    """data net"""

    def __init__(self, ds, net):
        super().__init__()
        self.x = ds.x
        self.in_deg = ds.in_deg
        self.out_deg = ds.out_deg
        self.train_mask = ms.Tensor(ds.train_mask, ms.float32)
        self.y = ds.y
        self.indptr = ds.indptr
        self.indices = ds.indices
        self.n_nodes = int(ds.n_nodes)
        self.net = net

    def construct(self):
        return self.net(self.x, self.in_deg, self.out_deg, self.train_mask, self.y,
                        self.n_nodes, self.indptr, self.indices)


def main(train_args):
    if train_args.fuse:
        context.set_context(device_target="GPU", save_graphs=True, save_graphs_path="./computational_graph/",
                            mode=context.GRAPH_MODE, enable_graph_kernel=True,
                            graph_kernel_flags="--enable_expand_ops=Gather --enable_cluster_ops=CSRReduceSum,CSRDiv "
                                               "--enable_recompute_fusion=false "
                                               "--enable_parallel_fusion=false "
                                               "--recompute_increment_threshold=40000000 "
                                               "--recompute_peak_threshold=3000000000 "
                                               "--enable_csr_fusion=true ")
    else:
        context.set_context(device_target="GPU", mode=context.PYNATIVE_MODE)
    # dataloader
    ds = GraphDataset(train_args.data_path)
    feature_size = ds.x.shape[1]
    if train_args.profile:
        ms_profiler = Profiler(subgraph="ALL", is_detail=True, is_show_op_path=False, output_path="./prof_result")
    # model
    net = GCNNet(data_feat_size=feature_size,
                 hidden_dim_size=train_args.num_hidden,
                 n_classes=ds.n_classes,
                 dropout=train_args.dropout,
                 activation=ms.nn.ELU,
                 indptr_backward=ds.indptr_backward,
                 indices_backward=ds.indices_backward)
    optimizer = nn.optim.Adam(net.trainable_params(), learning_rate=train_args.lr, weight_decay=train_args.weight_decay)
    loss = LossNet(net)
    train_net = nn.TrainOneStepCell(loss, optimizer)
    train_net = DataNet(ds, train_net)
    total = 0.
    warm_up = 3
    for e in range(train_args.epochs):
        beg = time.time()
        train_net.set_train()
        train_net.set_grad()
        train_loss = train_net()
        end = time.time()
        dur = end - beg
        if e >= warm_up:
            total = total + dur

        test_mask = ds.test_mask
        if test_mask is not None:
            net.set_train(False)
            out = net(ds.x, ds.in_deg, ds.out_deg, int(ds.n_nodes), ds.indptr, ds.indices).asnumpy()
            labels = ds.y.asnumpy()
            predict = np.argmax(out[test_mask], axis=1)
            label = labels[test_mask]
            count = np.equal(predict, label)
            print('Epoch time:{} ms Train loss {} Test acc:{}'.format(dur * 1000, train_loss,
                                                                      np.sum(count) / label.shape[0]))
        else:
            print('Epoch time:{} ms Train loss {}'.format(dur * 1000, train_loss))
    print("Model:{} Dataset:{} Avg epoch time:{}".format("GCN", train_args.data_path,
                                                         total * 1000 / (train_args.epochs - warm_up)))
    if train_args.profile:
        ms_profiler.analyse()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GCN")
    parser.add_argument("--data-path", type=str, default='/home/workspace/cora_v2_with_mask.npz',
                        help="path to dataloader")
    parser.add_argument("--gpu", type=int, default=0, help="which gpu to use")
    parser.add_argument("--dropout", type=float, default=0.5, help="drop out keep rate")
    parser.add_argument("--epochs", type=int, default=200, help="number of training epochs")
    parser.add_argument("--num-layers", type=int, default=1, help="number of hidden layers")
    parser.add_argument("--num-hidden", type=int, default=16, help="number of hidden units")
    parser.add_argument("--lr", type=float, default=1e-2, help="learning rate")
    parser.add_argument("--weight-decay", type=float, default=5e-4, help="weight decay")
    parser.add_argument('--profile', type=bool, default=False, help="feature dimension")
    parser.add_argument('--fuse', type=bool, default=False, help="enable fusion")
    args = parser.parse_args()
    print(args)
    main(args)