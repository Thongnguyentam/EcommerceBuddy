#!/bin/bash

# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the for the specific language governing permissions and
# limitations under the License.

set -e

# Generate Python gRPC code from proto files
python -m grpc_tools.protoc \
    --python_out=genproto \
    --grpc_python_out=genproto \
    --proto_path=protos \
    protos/review.proto

# Fix import paths in generated files
sed -i 's/import review_pb2/from . import review_pb2/g' genproto/review_pb2_grpc.py

echo "✅ Generated Python gRPC code successfully" 