mindspore_gl.nn.SumPooling
==========================

.. py:class:: mindspore_gl.nn.SumPooling

    将求和池化应用于批处理图形中的节点。

    .. math::
        r^{(i)} = \sum_{k=1}^{N_i} x^{(i)}_k

    输入：
        - **x** (Tensor) - 要更新的输入节点特征。Shape为 :math:`(N, D)`，
          其中 :math:`N` 是节点数， :math:`D` 是节点的特征大小。
        - **g** (BatchedGraph) - 输入图。

    输出：
        - **x** (Tensor) - 图形的输出表示。Shape为 :math:`(2, D_{out})`
          其中 :math:`D_{out}` 是节点的特征大小
