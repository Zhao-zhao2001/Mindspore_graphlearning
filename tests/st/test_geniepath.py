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
""" test geniepath """
import os
import shutil
import pytest

@pytest.mark.level0
@pytest.mark.platform_x86_gpu_training
@pytest.mark.env_onecard

def test_geniepath():
    """test geniepath"""
    if not os.path.exists('./ci_temp'):
        os.mkdir('ci_temp')
    if os.path.exists('ci_temp/geniepath'):
        shutil.rmtree('ci_temp/geniepath')

    cmd_copy = "cp -r ../../model_zoo/geniepath/ ./ci_temp/"
    os.system(cmd_copy)

    cmd_train = "python ./ci_temp/geniepath/trainval_pubmed.py " \
                "--data_path=\"/home/workspace/mindspore_dataset/GNN_Dataset/\" >> " \
                "./ci_temp/geniepath/trainval_pubmed.log"
    os.system(cmd_train)

    file = open("./ci_temp/geniepath/trainval_pubmed.log", "r")
    log_info = file.readlines()
    file.close()
    last_info = log_info[-1]
    test_acc = float(last_info[last_info.find('Test acc:'):].replace('Test acc:', '').replace('\n', ''))
    assert test_acc > 0.6
