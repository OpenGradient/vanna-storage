import onnx
from onnx import helper
from onnx import TensorProto
import numpy as np
import json

# Create a simple ONNX model
input = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 3])
output = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 3])
node = helper.make_node('Identity', ['input'], ['output'])
graph = helper.make_graph([node], 'test_model', [input], [output])
model = helper.make_model(graph)

# Save the ONNX model
onnx.save(model, 'test/test_model.onnx')