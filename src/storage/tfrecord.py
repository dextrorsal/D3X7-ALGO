import tensorflow as tf
import torch
import numpy as np
import json
import pandas as pd
import os
from torch.utils.data import Dataset, DataLoader

# ---- CREATING TFRECORDS FROM EXISTING DATA ----

def _bytes_feature(value):
    """Returns a bytes_list from a string / byte."""
    if isinstance(value, type(tf.constant(0))):
        value = value.numpy() 
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))

def _float_feature(value):
    """Returns a float_list from a float / double."""
    return tf.train.Feature(float_list=tf.train.FloatList(value=[value]))

def _int64_feature(value):
    """Returns an int64_list from a bool / enum / int / uint."""
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))

def _float_array_feature(value):
    return tf.train.Feature(float_list=tf.train.FloatList(value=value))

def _int64_array_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=value))

# Function to convert your data to TFRecord
def convert_to_tfrecord(data_dir, output_dir, records_per_file=1000):
    """
    Convert mixed data types to TFRecord format
    
    Args:
        data_dir: Directory containing .raw, .json, and .csv files
        output_dir: Directory to save TFRecord files
        records_per_file: Number of records per TFRecord file (for sharding)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all your data files
    raw_files = [f for f in os.listdir(data_dir) if f.endswith('.raw')]
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    
    # Example: Process CSV data
    all_data = []
    for csv_file in csv_files:
        df = pd.read_csv(os.path.join(data_dir, csv_file))
        # Convert each row to a dictionary
        for _, row in df.iterrows():
            all_data.append({
                'source': 'csv',
                'filename': csv_file,
                'data': row.to_dict()
            })
    
    # Process JSON data
    for json_file in json_files:
        with open(os.path.join(data_dir, json_file), 'r') as f:
            json_data = json.load(f)
            all_data.append({
                'source': 'json',
                'filename': json_file,
                'data': json_data
            })
    
    # Process RAW data
    for raw_file in raw_files:
        with open(os.path.join(data_dir, raw_file), 'rb') as f:
            raw_data = f.read()
            all_data.append({
                'source': 'raw',
                'filename': raw_file,
                'data': raw_data
            })
    
    # Write TFRecord files
    for i in range(0, len(all_data), records_per_file):
        shard = all_data[i:i+records_per_file]
        output_file = os.path.join(output_dir, f'data-{i//records_per_file:05d}.tfrecord')
        
        with tf.io.TFRecordWriter(output_file) as writer:
            for item in shard:
                # Create a feature dictionary based on data type
                if item['source'] == 'csv':
                    # For CSV data, serialize as JSON string
                    feature = {
                        'source': _bytes_feature(item['source'].encode('utf-8')),
                        'filename': _bytes_feature(item['filename'].encode('utf-8')),
                        'data': _bytes_feature(json.dumps(item['data']).encode('utf-8'))
                    }
                elif item['source'] == 'json':
                    # For JSON data, serialize as JSON string
                    feature = {
                        'source': _bytes_feature(item['source'].encode('utf-8')),
                        'filename': _bytes_feature(item['filename'].encode('utf-8')),
                        'data': _bytes_feature(json.dumps(item['data']).encode('utf-8'))
                    }
                elif item['source'] == 'raw':
                    # For raw binary data
                    feature = {
                        'source': _bytes_feature(item['source'].encode('utf-8')),
                        'filename': _bytes_feature(item['filename'].encode('utf-8')),
                        'data': _bytes_feature(item['data'])
                    }
                
                # Create an Example
                example = tf.train.Example(features=tf.train.Features(feature=feature))
                
                # Serialize the Example
                writer.write(example.SerializeToString())
        
        print(f"Created TFRecord file: {output_file}")

# ---- PYTORCH DATASET FOR TFRECORD ----

class TFRecordDataset(Dataset):
    def __init__(self, tfrecord_dir, transform=None):
        """
        PyTorch Dataset for TFRecord files
        
        Args:
            tfrecord_dir: Directory containing TFRecord files
            transform: Optional transform to apply to data
        """
        self.tfrecord_files = [os.path.join(tfrecord_dir, f) for f in os.listdir(tfrecord_dir) 
                              if f.endswith('.tfrecord')]
        self.transform = transform
        
        # Count total examples
        self.num_examples = 0
        for tfrecord_file in self.tfrecord_files:
            self.num_examples += sum(1 for _ in tf.data.TFRecordDataset(tfrecord_file))
        
        # Create index mapping
        self.index_mapping = []
        count = 0
        for file_idx, tfrecord_file in enumerate(self.tfrecord_files):
            file_count = sum(1 for _ in tf.data.TFRecordDataset(tfrecord_file))
            for i in range(file_count):
                self.index_mapping.append((file_idx, i))
                count += 1
    
    def __len__(self):
        return self.num_examples
    
    def __getitem__(self, idx):
        file_idx, example_idx = self.index_mapping[idx]
        tfrecord_file = self.tfrecord_files[file_idx]
        
        # Parse the record at the given index
        record = None
        for i, example in enumerate(tf.data.TFRecordDataset(tfrecord_file)):
            if i == example_idx:
                record = example.numpy()
                break
        
        if record is None:
            raise IndexError(f"Could not find record at index {example_idx} in file {tfrecord_file}")
        
        # Parse the example
        example = tf.train.Example()
        example.ParseFromString(record)
        
        # Extract features
        features = example.features.feature
        source = features['source'].bytes_list.value[0].decode('utf-8')
        filename = features['filename'].bytes_list.value[0].decode('utf-8')
        data = features['data'].bytes_list.value[0]
        
        # Process based on source
        if source == 'csv' or source == 'json':
            # Convert JSON string back to dictionary
            data = json.loads(data.decode('utf-8'))
        # For raw data, keep as bytes
        
        # Apply transform if provided
        if self.transform:
            data = self.transform(data)
        
        return {
            'source': source,
            'filename': filename,
            'data': data
        }

# ---- TENSORFLOW DATASET FOR TFRECORD ----

def get_tf_dataset(tfrecord_dir, batch_size=32):
    """
    Create a TensorFlow dataset from TFRecord files
    
    Args:
        tfrecord_dir: Directory containing TFRecord files
        batch_size: Batch size for the dataset
    
    Returns:
        tf.data.Dataset: TensorFlow dataset
    """
    tfrecord_files = [os.path.join(tfrecord_dir, f) for f in os.listdir(tfrecord_dir) 
                      if f.endswith('.tfrecord')]
    
    # Feature description for parsing
    feature_description = {
        'source': tf.io.FixedLenFeature([], tf.string),
        'filename': tf.io.FixedLenFeature([], tf.string),
        'data': tf.io.FixedLenFeature([], tf.string)
    }
    
    def _parse_function(example_proto):
        # Parse the input tf.Example proto
        parsed_features = tf.io.parse_single_example(example_proto, feature_description)
        
        # Process based on source (you might need custom logic here)
        source = parsed_features['source']
        filename = parsed_features['filename']
        data = parsed_features['data']
        
        return {
            'source': source,
            'filename': filename,
            'data': data
        }
    
    # Create dataset from TFRecord files
    dataset = tf.data.TFRecordDataset(tfrecord_files)
    dataset = dataset.map(_parse_function)
    dataset = dataset.batch(batch_size)
    
    return dataset

# ---- ADVANCED FEATURES ----

# 1. Compression for smaller file sizes
def create_compressed_tfrecord(data, output_file):
    options = tf.io.TFRecordOptions(compression_type='GZIP')
    with tf.io.TFRecordWriter(output_file, options=options) as writer:
        # Write examples as before
        pass

# 2. Parallel data loading with prefetching for PyTorch
class TFRecordDataModule:
    def __init__(self, tfrecord_dir, batch_size=32, num_workers=4):
        self.tfrecord_dir = tfrecord_dir
        self.batch_size = batch_size
        self.num_workers = num_workers
        
    def train_dataloader(self):
        dataset = TFRecordDataset(self.tfrecord_dir)
        return DataLoader(
            dataset,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            shuffle=True,
            pin_memory=True,
            prefetch_factor=2
        )

# 3. Efficient TensorFlow data pipeline
def get_optimized_tf_dataset(tfrecord_dir, batch_size=32):
    dataset = get_tf_dataset(tfrecord_dir, batch_size)
    # Optimize for performance
    dataset = dataset.cache()
    dataset = dataset.prefetch(tf.data.AUTOTUNE)
    return dataset

# ---- USAGE EXAMPLE ----

# Convert your data to TFRecord
convert_to_tfrecord(
    data_dir='/home/dex/ultimate_data_fetcher/data',
    output_dir='/home/dex/ultimate_data_fetcher/tfrecords',
    records_per_file=1000
)

# PyTorch usage
pytorch_dataset = TFRecordDataset('/home/dex/ultimate_data_fetcher/tfrecords')
pytorch_loader = DataLoader(pytorch_dataset, batch_size=32, shuffle=True)

for batch in pytorch_loader:
    # Process batch
    print(f"Batch contains {len(batch['source'])} examples")
    # Your PyTorch model processing here
    break

# TensorFlow usage
tf_dataset = get_tf_dataset('/home/dex/ultimate_data_fetcher/tfrecords')

for batch in tf_dataset:
    # Process batch
    print(f"TF batch contains {len(batch['source'])} examples")
    # Your TensorFlow model processing here
    break
