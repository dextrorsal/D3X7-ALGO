# src/backtesting/strategy_evaluator.py

import numpy as np
import pandas as pd
from typing import Callable, Dict, List, Tuple, Union
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor
import random


class StrategyEvaluator:
    """
    A comprehensive framework for evaluating trading strategies using the four-step process
    as outlined in the strategy development methodology:
    
    1. Insample Excellence (optimization)
    2. Insample Monte Carlo Permutation Test (validate against random chance)
    3. Walk Forward Test (out-of-sample testing)
    4. Walk Forward Monte Carlo Permutation Test (validate walk forward against random chance)
    """
    
    def __init__(self, data: pd.DataFrame, strategy_func: Callable, param_grid: Dict[str, List], 
                 objective_func: Callable = None, training_window_days: int = 365*4,
                 step_days: int = 90, n_permutations: int = 200):
        """
        Initialize the StrategyEvaluator.
        
        Args:
            data: DataFrame with OHLCV data (must have 'close' column and DatetimeIndex)
            strategy_func: Function that generates signals based on data and parameters
            param_grid: Dictionary of parameter names and lists of values to test
            objective_func: Function to evaluate strategy performance (default: profit_factor)
            training_window_days: Number of days in each training window for walk forward testing
            step_days: Number of days to step forward in each walk forward iteration
            n_permutations: Number of permutations for Monte Carlo tests
        """
        self.data = data
        self.strategy_func = strategy_func
        self.param_grid = param_grid
        self.objective_func = objective_func if objective_func else self.profit_factor
        self.training_window_days = training_window_days
        self.step_days = step_days
        self.n_permutations = n_permutations
        self.results = {}
        
    def profit_factor(self, returns: np.ndarray) -> float:
        """Calculate profit factor (sum of positive returns / sum of negative returns)"""
        positive_returns = returns[returns > 0].sum()
        negative_returns = abs(returns[returns < 0].sum())
        
        if negative_returns == 0:
            return float('inf') if positive_returns > 0 else 0
            
        return positive_returns / negative_returns
        
    def sharpe_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sharpe ratio (mean return / standard deviation)"""
        if len(returns) < 2 or returns.std() == 0:
            return 0
        return (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized
    
    def grid_search(self, data: pd.DataFrame) -> Dict:
        """
        Perform grid search to find optimal parameters.
        
        Args:
            data: DataFrame with price data to optimize on
            
        Returns:
            Dictionary with best parameters and their performance
        """
        best_score = -float('inf')
        best_params = None
        all_results = []
        
        # Generate all parameter combinations
        param_keys = list(self.param_grid.keys())
        param_values = list(self.param_grid.values())
        
        # Track all results for later analysis
        for values in self._generate_param_combinations(param_values):
            params = dict(zip(param_keys, values))
            
            # Generate signals using the strategy function
            signals = self.strategy_func(data, **params)
            
            # Calculate returns (assuming signals are aligned with data)
            returns = data['close'].pct_change().shift(-1).values * signals
            returns = returns[~np.isnan(returns)]
            
            if len(returns) == 0:
                continue
                
            # Calculate objective score
            score = self.objective_func(returns)
            
            result = {**params, 'score': score}
            all_results.append(result)
            
            # Update best parameters if score is higher
            if score > best_score:
                best_score = score
                best_params = params
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'all_results': all_results
        }
    
    def _generate_param_combinations(self, param_values, i=0, current=None):
        """Recursively generate all parameter combinations"""
        if current is None:
            current = []
            
        if i == len(param_values):
            yield current
            return
            
        for value in param_values[i]:
            yield from self._generate_param_combinations(param_values, i+1, current + [value])
    
    def permute_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Create a permutation of the data preserving some statistical properties.
        
        The algorithm:
        1. Compute log returns
        2. Shuffle the indices of returns
        3. Reconstruct prices from shuffled returns
        
        Args:
            data: DataFrame with price data
            
        Returns:
            DataFrame with permuted price data
        """
        # Calculate log returns
        log_returns = np.log(data['close'] / data['close'].shift(1))
        log_returns = log_returns.iloc[1:]  # Remove NaN
        
        # Create a copy of the dataframe
        permuted_data = data.copy()
        
        # Shuffle the indices
        shuffled_indices = log_returns.index.tolist()
        random.shuffle(shuffled_indices)
        shuffled_returns = log_returns.loc[shuffled_indices].values
        
        # Reconstruct prices
        first_price = data['close'].iloc[0]
        prices = [first_price]
        
        for ret in shuffled_returns:
            prices.append(prices[-1] * np.exp(ret))
            
        # Create a new dataframe with original index but permuted prices
        permuted_data['close'] = pd.Series(
            prices + [prices[-1]] * (len(data) - len(prices)), 
            index=data.index
        )
        
        # Adjust other OHLC values proportionally if they exist
        if 'open' in permuted_data.columns:
            ratio = permuted_data['close'] / data['close']
            for col in ['open', 'high', 'low']:
                if col in permuted_data.columns:
                    permuted_data[col] = data[col] * ratio
        
        return permuted_data
    
    def insample_monte_carlo(self, data: pd.DataFrame, best_params: Dict) -> Dict:
        """
        Perform insample Monte Carlo permutation test.
        
        Args:
            data: DataFrame with price data
            best_params: Best parameters found in grid search
            
        Returns:
            Dictionary with p-value and distribution statistics
        """
        # Get performance on original data
        signals = self.strategy_func(data, **best_params)
        original_returns = data['close'].pct_change().shift(-1).values * signals
        original_returns = original_returns[~np.isnan(original_returns)]
        original_score = self.objective_func(original_returns)
        
        # Create permutations and evaluate strategy on each
        permutation_scores = []
        
        for i in range(self.n_permutations):
            # Create permuted data
            permuted_data = self.permute_data(data)
            
            # Run strategy on permuted data
            signals = self.strategy_func(permuted_data, **best_params)
            perm_returns = permuted_data['close'].pct_change().shift(-1).values * signals
            perm_returns = perm_returns[~np.isnan(perm_returns)]
            
            if len(perm_returns) > 0:
                score = self.objective_func(perm_returns)
                permutation_scores.append(score)
        
        # Calculate p-value (proportion of permutations that performed better)
        count_better = sum(1 for score in permutation_scores if score >= original_score)
        p_value = count_better / len(permutation_scores) if permutation_scores else 1.0
        
        return {
            'original_score': original_score,
            'permutation_scores': permutation_scores,
            'p_value': p_value,
            'mean': np.mean(permutation_scores) if permutation_scores else 0,
            'std': np.std(permutation_scores) if permutation_scores else 0
        }
    
    def walk_forward_test(self) -> Dict:
        """
        Perform walk forward testing.
        
        Returns:
            Dictionary with walk forward test results
        """
        data = self.data
        results = []
        dates = []
        params_history = []
        
        # Convert days to periods based on data frequency
        freq = pd.infer_freq(data.index)
        periods_per_day = 1
        if freq == 'H':
            periods_per_day = 24
        elif freq == 'min' or freq == 'T':
            periods_per_day = 24 * 60
        
        training_window = self.training_window_days * periods_per_day
        step_size = self.step_days * periods_per_day
        
        # Ensure we have enough data
        if len(data) < training_window:
            raise ValueError(f"Not enough data for training window of {self.training_window_days} days")
        
        i = 0
        while i + training_window < len(data):
            # Define training and test sets
            train_data = data.iloc[i:i+training_window]
            
            # Determine test end index
            test_end = min(i + training_window + step_size, len(data))
            test_data = data.iloc[i+training_window:test_end]
            
            if len(test_data) == 0:
                break
                
            # Optimize on training data
            opt_result = self.grid_search(train_data)
            best_params = opt_result['best_params']
            params_history.append(best_params)
            
            # Test on out-of-sample data
            signals = self.strategy_func(test_data, **best_params)
            returns = test_data['close'].pct_change().shift(-1).values * signals
            returns = returns[~np.isnan(returns)]
            
            if len(returns) > 0:
                score = self.objective_func(returns)
                results.append(score)
                dates.append(test_data.index[-1])
            
            # Move to next step
            i += step_size
        
        # Calculate overall performance metrics
        all_returns = []
        for i in range(len(results)):
            train_end = i * step_size + training_window
            test_end = min(train_end + step_size, len(data))
            test_data = data.iloc[train_end:test_end]
            
            signals = self.strategy_func(test_data, **params_history[i])
            returns = test_data['close'].pct_change().shift(-1).values * signals
            returns = returns[~np.isnan(returns)]
            all_returns.extend(returns)
        
        all_returns = np.array(all_returns)
        overall_score = self.objective_func(all_returns) if len(all_returns) > 0 else 0
        
        return {
            'step_results': results,
            'dates': dates,
            'params_history': params_history,
            'overall_score': overall_score,
            'all_returns': all_returns
        }
    
    def walk_forward_permutation_test(self) -> Dict:
        """
        Perform walk forward Monte Carlo permutation test.
        
        Returns:
            Dictionary with walk forward permutation test results
        """
        # Get original walk forward results
        wf_results = self.walk_forward_test()
        original_score = wf_results['overall_score']
        
        # Perform permutation tests
        permutation_scores = []
        
        for i in range(self.n_permutations):
            # Create a copy of the data for permutation
            permuted_data = self.data.copy()
            
            # Get the date of the first training fold end
            train_end_idx = self.training_window_days * 1  # Adjust for data frequency
            
            # Only permute the data after the first training fold
            permuted_part = self.permute_data(permuted_data.iloc[train_end_idx:])
            
            # Combine the original training data with the permuted test data
            permuted_data = pd.concat([
                permuted_data.iloc[:train_end_idx],
                permuted_part
            ])
            
            # Create a temporary optimizer for this permutation
            temp_optimizer = StrategyEvaluator(
                permuted_data, self.strategy_func, self.param_grid,
                self.objective_func, self.training_window_days,
                self.step_days, 1  # Only need 1 permutation here
            )
            
            # Run walk forward test on permuted data
            perm_wf_results = temp_optimizer.walk_forward_test()
            perm_score = perm_wf_results['overall_score']
            permutation_scores.append(perm_score)
        
        # Calculate p-value
        count_better = sum(1 for score in permutation_scores if score >= original_score)
        p_value = count_better / len(permutation_scores) if permutation_scores else 1.0
        
        return {
            'original_score': original_score,
            'permutation_scores': permutation_scores,
            'p_value': p_value,
            'mean': np.mean(permutation_scores) if permutation_scores else 0,
            'std': np.std(permutation_scores) if permutation_scores else 0
        }
    
    def run_full_analysis(self) -> Dict:
        """
        Run the complete 4-step analysis process.
        
        Returns:
            Dictionary with complete analysis results
        """
        # Step 1: Insample Excellence (Grid Search)
        print("Step 1: Running Insample Excellence...")
        insample_results = self.grid_search(self.data)
        
        # Step 2: Insample Monte Carlo Permutation Test
        print("Step 2: Running Insample Monte Carlo Permutation Test...")
        mc_results = self.insample_monte_carlo(self.data, insample_results['best_params'])
        
        # Step 3: Walk Forward Test
        print("Step 3: Running Walk Forward Test...")
        wf_results = self.walk_forward_test()
        
        # Step 4: Walk Forward Monte Carlo Permutation Test
        print("Step 4: Running Walk Forward Monte Carlo Permutation Test...")
        wf_mc_results = self.walk_forward_permutation_test()
        
        self.results = {
            'insample_excellence': insample_results,
            'insample_monte_carlo': mc_results,
            'walk_forward': wf_results,
            'walk_forward_monte_carlo': wf_mc_results
        }
        
        return self.results
    
    def plot_results(self) -> None:
        """Plot analysis results"""
        if not self.results:
            print("No results to plot. Run analysis first.")
            return
            
        fig, axs = plt.subplots(2, 2, figsize=(15, 10))
        
        # Plot 1: Parameter Optimization Results
        insample_results = self.results['insample_excellence']['all_results']
        param_key = list(self.param_grid.keys())[0]  # Just plot first parameter for simplicity
        
        param_values = [result[param_key] for result in insample_results]
        scores = [result['score'] for result in insample_results]
        
        axs[0, 0].scatter(param_values, scores)
        axs[0, 0].set_title('Parameter Optimization')
        axs[0, 0].set_xlabel(param_key)
        axs[0, 0].set_ylabel('Objective Score')
        
        # Plot 2: Insample Monte Carlo Histogram
        mc_results = self.results['insample_monte_carlo']
        axs[0, 1].hist(mc_results['permutation_scores'], bins=20, alpha=0.7)
        axs[0, 1].axvline(mc_results['original_score'], color='r', linestyle='dashed', 
                          label=f'Original (p={mc_results["p_value"]:.2f})')
        axs[0, 1].set_title('Insample Monte Carlo')
        axs[0, 1].set_xlabel('Score')
        axs[0, 1].set_ylabel('Frequency')
        axs[0, 1].legend()
        
        # Plot 3: Walk Forward Results
        wf_results = self.results['walk_forward']
        dates = wf_results['dates']
        scores = wf_results['step_results']
        
        if dates and scores:
            axs[1, 0].plot(dates, scores, marker='o')
            axs[1, 0].set_title('Walk Forward Test')
            axs[1, 0].set_xlabel('Date')
            axs[1, 0].set_ylabel('Objective Score')
            axs[1, 0].axhline(1.0, color='k', linestyle='--', alpha=0.3)
            
            # Rotate date labels for better readability
            plt.setp(axs[1, 0].xaxis.get_majorticklabels(), rotation=45)
        else:
            axs[1, 0].text(0.5, 0.5, 'No Walk Forward Results', 
                           horizontalalignment='center', verticalalignment='center')
        
        # Plot 4: Walk Forward Monte Carlo Histogram
        wf_mc_results = self.results['walk_forward_monte_carlo']
        axs[1, 1].hist(wf_mc_results['permutation_scores'], bins=20, alpha=0.7)
        axs[1, 1].axvline(wf_mc_results['original_score'], color='r', linestyle='dashed',
                          label=f'Original (p={wf_mc_results["p_value"]:.2f})')
        axs[1, 1].set_title('Walk Forward Monte Carlo')
        axs[1, 1].set_xlabel('Score')
        axs[1, 1].set_ylabel('Frequency')
        axs[1, 1].legend()
        
        plt.tight_layout()
        plt.show()
        
    def summary(self) -> str:
        """Generate a summary of the analysis results"""
        if not self.results:
            return "No results available. Run analysis first."
            
        insample = self.results['insample_excellence']
        insample_mc = self.results['insample_monte_carlo']
        wf = self.results['walk_forward']
        wf_mc = self.results['walk_forward_monte_carlo']
        
        summary = "TRADING STRATEGY EVALUATION SUMMARY\n"
        summary += "=" * 40 + "\n\n"
        
        # Step 1: Insample Excellence
        summary += "STEP 1: INSAMPLE EXCELLENCE\n"
        summary += "-" * 30 + "\n"
        summary += f"Best Parameters: {insample['best_params']}\n"
        summary += f"Best Score: {insample['best_score']:.4f}\n\n"
        
        # Step 2: Insample Monte Carlo
        summary += "STEP 2: INSAMPLE MONTE CARLO TEST\n"
        summary += "-" * 30 + "\n"
        summary += f"Original Score: {insample_mc['original_score']:.4f}\n"
        summary += f"Permutation Mean: {insample_mc['mean']:.4f}\n"
        summary += f"Permutation Std: {insample_mc['std']:.4f}\n"
        summary += f"P-value: {insample_mc['p_value']:.4f}\n"
        if insample_mc['p_value'] < 0.05:
            summary += "RESULT: Strategy shows significant evidence against null hypothesis.\n\n"
        else:
            summary += "RESULT: Strategy does not show significant evidence against null hypothesis.\n\n"
        
        # Step 3: Walk Forward Test
        summary += "STEP 3: WALK FORWARD TEST\n"
        summary += "-" * 30 + "\n"
        summary += f"Overall Score: {wf['overall_score']:.4f}\n"
        if len(wf['step_results']) > 0:
            summary += f"Min Step Score: {min(wf['step_results']):.4f}\n"
            summary += f"Max Step Score: {max(wf['step_results']):.4f}\n"
            summary += f"Mean Step Score: {np.mean(wf['step_results']):.4f}\n"
        summary += "\n"
        
        # Step 4: Walk Forward Monte Carlo
        summary += "STEP 4: WALK FORWARD MONTE CARLO TEST\n"
        summary += "-" * 30 + "\n"
        summary += f"Original Score: {wf_mc['original_score']:.4f}\n"
        summary += f"Permutation Mean: {wf_mc['mean']:.4f}\n"
        summary += f"Permutation Std: {wf_mc['std']:.4f}\n"
        summary += f"P-value: {wf_mc['p_value']:.4f}\n"
        if wf_mc['p_value'] < 0.05:
            summary += "RESULT: Walk forward results show significant evidence against null hypothesis.\n\n"
        else:
            summary += "RESULT: Walk forward results do not show significant evidence against null hypothesis.\n\n"
        
        # Final Assessment
        summary += "FINAL ASSESSMENT\n"
        summary += "=" * 30 + "\n"
        
        if insample_mc['p_value'] < 0.05 and wf_mc['p_value'] < 0.05 and wf['overall_score'] > 1.0:
            summary += "EXCELLENT: Strategy passes all tests with significant evidence.\n"
        elif insample_mc['p_value'] < 0.1 and wf_mc['p_value'] < 0.1 and wf['overall_score'] > 1.0:
            summary += "GOOD: Strategy passes tests with moderate evidence.\n"
        elif wf['overall_score'] > 1.0:
            summary += "MARGINAL: Strategy is profitable in walk forward testing but lacks statistical significance.\n"
        else:
            summary += "POOR: Strategy does not demonstrate consistent profitability or statistical significance.\n"
            
        return summary