import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from pathlib import Path
import matplotlib.pyplot as plt
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

class TradingDataset(Dataset):
    """
    Dataset for trading data that includes indicator signals and prices.
    This class prepares your data for PyTorch training.
    """
    def __init__(self, features: np.ndarray, labels: np.ndarray):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.float32)
        
    def __len__(self):
        return len(self.features)
        
    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]


class TradingModel(nn.Module):
    """
    Neural network model for trading that can handle both classification and regression.
    
    This model contains:
    - Separate paths for classification and regression tasks
    - Shared base layers for feature extraction
    - Configurable architecture based on your needs
    """
    def __init__(self, input_size: int, hidden_size: int = 64, 
                 num_layers: int = 2, dropout: float = 0.2):
        super(TradingModel, self).__init__()
        
        # Shared base layers
        layers = []
        layers.append(nn.Linear(input_size, hidden_size))
        layers.append(nn.ReLU())
        layers.append(nn.BatchNorm1d(hidden_size))
        layers.append(nn.Dropout(dropout))
        
        for _ in range(num_layers - 1):
            layers.append(nn.Linear(hidden_size, hidden_size))
            layers.append(nn.ReLU())
            layers.append(nn.BatchNorm1d(hidden_size))
            layers.append(nn.Dropout(dropout))
            
        self.base = nn.Sequential(*layers)
        
        # Classification head (direction prediction: up/down)
        self.classification_head = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        # Regression head (magnitude prediction)
        self.regression_head = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1)
        )
        
    def forward(self, x):
        """Forward pass through the model"""
        features = self.base(x)
        
        # Get classification and regression outputs
        class_output = self.classification_head(features)
        regr_output = self.regression_head(features)
        
        return class_output, regr_output


class CryptoTradingModel:
    """
    Complete trading model manager that handles:
    - Data preparation
    - Model training
    - Prediction
    - Evaluation
    - Integration with your existing indicators
    """
    def __init__(self, config: dict = None):
        """
        Initialize the trading model with configuration.
        """
        self.config = config or {
            'hidden_size': 64,
            'num_layers': 2,
            'dropout': 0.2,
            'learning_rate': 0.001,
            'batch_size': 64,
            'num_epochs': 50,
            'train_test_split': 0.2,
            'class_weight': 1.0,
            'regr_weight': 0.5
        }
        
        self.model = None
        self.scaler = StandardScaler()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")
        
    def prepare_data(self, df: pd.DataFrame, 
                    feature_columns: List[str],
                    target_column: str,
                    lookback: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare data for model training by creating feature sequences and labels.
        
        Args:
            df: DataFrame with indicator signals and price data
            feature_columns: List of column names to use as features
            target_column: Column name to predict (usually 'close')
            lookback: Number of time steps to include in each feature sequence
            
        Returns:
            X: Feature sequences
            y: Target labels (direction and magnitude)
        """
        # Extract features and target
        data = df[feature_columns + [target_column]].values
        
        X = []
        y = []
        
        # Create sequences with lookback
        for i in range(len(data) - lookback):
            # Features: lookback window of all feature columns
            features = data[i:i+lookback, :-1]
            
            # Target: price after lookback window
            current_price = data[i+lookback-1, -1]
            next_price = data[i+lookback, -1]
            
            # Calculate price direction (1 for up, 0 for down) and percent change
            price_direction = 1 if next_price > current_price else 0
            price_change = (next_price - current_price) / current_price
            
            # Flatten the features (from 2D to 1D)
            X.append(features.flatten())
            y.append([price_direction, price_change])
        
        return np.array(X), np.array(y)
    
    def train(self, df: pd.DataFrame, feature_columns: List[str], 
              target_column: str = 'close', lookback: int = 10) -> Dict:
        """
        Train the model using your trading data.
        
        Args:
            df: DataFrame with indicator signals and price data
            feature_columns: List of column names to use as features
            target_column: Column name to predict (usually 'close')
            lookback: Number of time steps to use for prediction
            
        Returns:
            Dict with training history
        """
        # Prepare data
        X, y = self.prepare_data(df, feature_columns, target_column, lookback)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=self.config['train_test_split'], shuffle=False
        )
        
        # Create datasets and dataloaders
        train_dataset = TradingDataset(X_train, y_train)
        test_dataset = TradingDataset(X_test, y_test)
        
        train_loader = DataLoader(
            train_dataset, 
            batch_size=self.config['batch_size'], 
            shuffle=True
        )
        
        test_loader = DataLoader(
            test_dataset, 
            batch_size=self.config['batch_size'], 
            shuffle=False
        )
        
        # Initialize model
        input_size = X_train.shape[1]
        self.model = TradingModel(
            input_size=input_size,
            hidden_size=self.config['hidden_size'],
            num_layers=self.config['num_layers'],
            dropout=self.config['dropout']
        ).to(self.device)
        
        # Define loss functions and optimizer
        classification_loss_fn = nn.BCELoss()
        regression_loss_fn = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=self.config['learning_rate'])
        
        # Training loop
        history = {
            'train_loss': [],
            'test_loss': [],
            'class_accuracy': [],
            'regr_mse': []
        }
        
        for epoch in range(self.config['num_epochs']):
            # Training
            self.model.train()
            train_loss = 0.0
            
            for features, targets in train_loader:
                features = features.to(self.device)
                class_targets = targets[:, 0:1].to(self.device)
                regr_targets = targets[:, 1:].to(self.device)
                
                # Forward pass
                class_outputs, regr_outputs = self.model(features)
                
                # Calculate losses
                class_loss = classification_loss_fn(class_outputs, class_targets)
                regr_loss = regression_loss_fn(regr_outputs, regr_targets)
                
                # Combined loss with weights
                loss = (self.config['class_weight'] * class_loss + 
                        self.config['regr_weight'] * regr_loss)
                
                # Backward pass and optimize
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            # Evaluation
            self.model.eval()
            test_loss = 0.0
            correct_preds = 0
            total_preds = 0
            regr_mse = 0.0
            
            with torch.no_grad():
                for features, targets in test_loader:
                    features = features.to(self.device)
                    class_targets = targets[:, 0:1].to(self.device)
                    regr_targets = targets[:, 1:].to(self.device)
                    
                    # Forward pass
                    class_outputs, regr_outputs = self.model(features)
                    
                    # Calculate losses
                    class_loss = classification_loss_fn(class_outputs, class_targets)
                    regr_loss = regression_loss_fn(regr_outputs, regr_targets)
                    
                    # Combined loss
                    loss = (self.config['class_weight'] * class_loss + 
                            self.config['regr_weight'] * regr_loss)
                    
                    test_loss += loss.item()
                    
                    # Calculate classification accuracy
                    predicted = (class_outputs > 0.5).float()
                    correct_preds += (predicted == class_targets).sum().item()
                    total_preds += class_targets.size(0)
                    
                    # Calculate regression MSE
                    regr_mse += ((regr_outputs - regr_targets) ** 2).mean().item()
            
            # Record metrics
            avg_train_loss = train_loss / len(train_loader)
            avg_test_loss = test_loss / len(test_loader)
            accuracy = correct_preds / total_preds if total_preds > 0 else 0
            avg_regr_mse = regr_mse / len(test_loader)
            
            history['train_loss'].append(avg_train_loss)
            history['test_loss'].append(avg_test_loss)
            history['class_accuracy'].append(accuracy)
            history['regr_mse'].append(avg_regr_mse)
            
            # Print progress
            if (epoch + 1) % 10 == 0 or epoch == 0:
                print(f"Epoch [{epoch+1}/{self.config['num_epochs']}], "
                      f"Train Loss: {avg_train_loss:.4f}, "
                      f"Test Loss: {avg_test_loss:.4f}, "
                      f"Accuracy: {accuracy:.4f}, "
                      f"Regression MSE: {avg_regr_mse:.4f}")
        
        print("Training completed!")
        return history
    
    def save_model(self, path: str):
        """Save the trained model to a file"""
        if self.model is not None:
            # Save model state
            model_state = {
                'model_state_dict': self.model.state_dict(),
                'config': self.config,
                'scaler': self.scaler
            }
            torch.save(model_state, path)
            print(f"Model saved to {path}")
        else:
            print("No model to save. Please train a model first.")
    
    def load_model(self, path: str):
        """Load a trained model from a file"""
        if Path(path).exists():
            # Load model state
            model_state = torch.load(path, map_location=self.device)
            
            # Extract configuration and scaler
            self.config = model_state['config']
            self.scaler = model_state['scaler']
            
            # Create model with the right architecture
            input_size = next(iter(model_state['model_state_dict'].values())).shape[1]
            self.model = TradingModel(
                input_size=input_size,
                hidden_size=self.config['hidden_size'],
                num_layers=self.config['num_layers'],
                dropout=self.config['dropout']
            ).to(self.device)
            
            # Load model weights
            self.model.load_state_dict(model_state['model_state_dict'])
            self.model.eval()
            
            print(f"Model loaded from {path}")
        else:
            print(f"No model found at {path}")
    
    def predict(self, features: np.ndarray) -> Tuple[float, float]:
        """
        Make a prediction using the trained model.
        
        Args:
            features: Feature array with shape matching the training data
            
        Returns:
            Tuple of (direction_probability, predicted_change)
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded. Call train() or load_model() first.")
        
        # Prepare features
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        features_tensor = torch.tensor(features_scaled, dtype=torch.float32).to(self.device)
        
        # Make prediction
        self.model.eval()
        with torch.no_grad():
            class_output, regr_output = self.model(features_tensor)
            
        # Extract prediction values
        direction_prob = class_output.item()
        predicted_change = regr_output.item()
        
        return direction_prob, predicted_change
    
    def get_signal(self, features: np.ndarray, threshold: float = 0.6) -> int:
        """
        Get a trading signal from the model prediction.
        
        Args:
            features: Feature array
            threshold: Probability threshold for generating signals (0.5-0.7 recommended)
            
        Returns:
            1 for buy, -1 for sell, 0 for hold
        """
        direction_prob, predicted_change = self.predict(features)
        
        # Generate signal based on prediction
        if direction_prob > threshold:
            return 1  # Buy signal
        elif direction_prob < (1 - threshold):
            return -1  # Sell signal
        else:
            return 0  # Hold/neutral
    
    def plot_training_history(self, history: Dict):
        """Plot training metrics history"""
        plt.figure(figsize=(15, 10))
        
        # Plot training and test loss
        plt.subplot(2, 2, 1)
        plt.plot(history['train_loss'], label='Train Loss')
        plt.plot(history['test_loss'], label='Test Loss')
        plt.title('Model Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        
        # Plot classification accuracy
        plt.subplot(2, 2, 2)
        plt.plot(history['class_accuracy'])
        plt.title('Classification Accuracy')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        
        # Plot regression MSE
        plt.subplot(2, 2, 3)
        plt.plot(history['regr_mse'])
        plt.title('Regression MSE')
        plt.xlabel('Epoch')
        plt.ylabel('MSE')
        
        plt.tight_layout()
        plt.show()
        
    def feature_importance(self, X: np.ndarray, feature_names: List[str]) -> Dict[str, float]:
        """
        Estimate feature importance by measuring prediction changes when features are perturbed.
        
        Args:
            X: Feature data
            feature_names: List of feature names corresponding to columns in X
            
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded")
            
        importance = {}
        X_scaled = self.scaler.transform(X)
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32).to(self.device)
        
        # Get baseline prediction
        self.model.eval()
        with torch.no_grad():
            base_class, base_regr = self.model(X_tensor)
            
        # Calculate impact of each feature
        for i, name in enumerate(feature_names):
            # Create perturbed feature
            X_perturbed = X_scaled.copy()
            X_perturbed[:, i] = np.random.permutation(X_perturbed[:, i])
            X_perturbed_tensor = torch.tensor(X_perturbed, dtype=torch.float32).to(self.device)
            
            # Get prediction with perturbed feature
            with torch.no_grad():
                perturbed_class, perturbed_regr = self.model(X_perturbed_tensor)
                
            # Calculate change in outputs
            class_diff = torch.abs(base_class - perturbed_class).mean().item()
            regr_diff = torch.abs(base_regr - perturbed_regr).mean().item()
            
            # Combined importance
            importance[name] = (self.config['class_weight'] * class_diff + 
                               self.config['regr_weight'] * regr_diff)
            
        # Normalize importance scores
        total = sum(importance.values())
        if total > 0:
            importance = {k: v / total for k, v in importance.items()}
            
        # Sort by importance (descending)
        return dict(sorted(importance.items(), key=lambda item: item[1], reverse=True))


# Example usage code
def prepare_indicator_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract and prepare features from your indicator data.
    This is an example of how to transform your indicators into model features.
    
    Args:
        df: DataFrame containing OHLCV data and indicator signals
        
    Returns:
        DataFrame with features ready for the model
    """
    features = pd.DataFrame(index=df.index)
    
    # Price-based features
    features['return_1d'] = df['close'].pct_change(1)
    features['return_5d'] = df['close'].pct_change(5)
    features['return_10d'] = df['close'].pct_change(10)
    features['volatility'] = df['close'].pct_change().rolling(10).std()
    
    # Volume features (if available)
    if 'volume' in df.columns:
        features['volume_change'] = df['volume'].pct_change(1)
        features['volume_ma_ratio'] = df['volume'] / df['volume'].rolling(10).mean()
    
    # Technical indicators (assuming these are already in your DataFrame)
    indicator_columns = [
        'macd', 'macd_signal', 'macd_hist',  # MACD indicators
        'rsi', 'bb_upper', 'bb_middle', 'bb_lower',  # RSI and Bollinger Bands
        'supertrend', 'lorentzian_signal',    # Your custom indicators
        'adx', 'williams_r'                   # Other indicators
    ]
    
    # Add any indicators that exist in the DataFrame
    for col in indicator_columns:
        if col in df.columns:
            features[col] = df[col]
    
    # Add indicator signals if they exist
    signal_columns = [col for col in df.columns if col.endswith('_signal')]
    for col in signal_columns:
        features[col] = df[col]
    
    # Drop NaN values (important for training)
    features = features.dropna()
    
    return features


def example_model_training():
    """Example function showing how to use the model with your data"""
    
    # Load your data
    # This is a placeholder - replace with your actual data loading code
    from src.storage.processed import ProcessedDataStorage
    from src.core.config import StorageConfig
    from datetime import datetime, timedelta
    import asyncio
    
    # Initialize storage
    config = StorageConfig()
    storage = ProcessedDataStorage(config)
    
    # Define date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 90 days of data
    
    # Load SOL/USDT data
    async def load_data():
        df = await storage.load_candles(
            exchange="binance", 
            market="SOL/USDT", 
            resolution="1h",  # Hourly data
            start_time=start_date,
            end_time=end_date
        )
        return df
    
    # Run the async function to get data
    df = asyncio.run(load_data())
    
    # Calculate indicators (assuming you have functions for this)
    # This is placeholder code - replace with your actual indicator calculation
    from src.utils.indicators import RsiIndicator, SupertrendIndicator, MacdIndicator
    
    rsi = RsiIndicator()
    supertrend = SupertrendIndicator()
    macd = MacdIndicator()
    
    df['rsi_signal'] = rsi.generate_signals(df)
    df['supertrend_signal'] = supertrend.generate_signals(df)
    df['macd_signal'] = macd.generate_signals(df)
    
    # Prepare features
    features_df = prepare_indicator_features(df)
    
    # Define feature columns to use
    feature_columns = [col for col in features_df.columns if col != 'close']
    
    # Initialize and train the model
    model = CryptoTradingModel()
    history = model.train(
        df=features_df,
        feature_columns=feature_columns,
        target_column='close',
        lookback=10
    )
    
    # Plot training history
    model.plot_training_history(history)
    
    # Save the model
    model.save_model('models/sol_trading_model.pth')
    
    # Calculate feature importance
    X, y = model.prepare_data(features_df, feature_columns, 'close', lookback=10)
    importance = model.feature_importance(X, feature_columns)
    
    # Print feature importance
    print("\nFeature Importance:")
    for feature, score in importance.items():
        print(f"{feature}: {score:.4f}")
    
    print("\nModel training and evaluation complete!")


if __name__ == "__main__":
    # This will run the example when you execute this file directly
    example_model_training()