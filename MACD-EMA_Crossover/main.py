#region imports
from AlgorithmImports import *
#endregion

MACD_MA_FAST = 12
MACD_MA_SLOW = 26
MACD_MA_SIGNAL = 9

COARSE_COUNT = 500

class MACD_EMA_Crossover(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2019, 1, 1)
        self.SetEndDate(2023, 1, 1)
        self.SetCash(10000000)

        self.AddUniverse(self.CoarseSelectionFunction)
        self.UniverseSettings.Resolution = Resolution.Daily

        self.averages = {}
    
    def CoarseSelectionFunction(self, coarse):
        selected = []
        universe = sorted(
            [
                x
                for x in coarse
                if x.HasFundamentalData and x.Market == "usa" and x.Price > 10
            ], key=lambda c: c.DollarVolume, reverse=True)

        for coarse in universe:
            symbol = coarse.Symbol
            
            if symbol not in self.averages:
                history = self.History(symbol, 200, Resolution.Daily)
                self.averages[symbol] = SelectionData(history) 

            self.averages[symbol].update(self.Time, coarse.AdjustedPrice)
            
            if self.averages[symbol].is_ready() and self.averages[symbol].fast > self.averages[symbol].slow:
                selected.append(symbol)
        
        return selected[:COARSE_COUNT]
        
    def OnData(self, data):
        for symbol, symbol_data in self.averages.items():
            if self.Portfolio.ContainsKey(symbol):
                holdings = self.Portfolio[symbol].Quantity
            else:
                holdings = 0
            
            signalDeltaPercent = (symbol_data.macd.Current.Value - symbol_data.macd.Signal.Current.Value)/symbol_data.macd.Fast.Current.Value
            tolerance = 0.0025

            if holdings <= 0 and signalDeltaPercent > tolerance:
                invested = [x.Key for x in self.Portfolio if x.Value.Invested]
                if len(invested) == 0:
                    self.SetHoldings(symbol, 1 / COARSE_COUNT)
                else:
                    self.SetHoldings(symbol, 1 / len(invested))
            elif holdings >= 0 and signalDeltaPercent < -tolerance:
                self.Liquidate(symbol)
                

class SelectionData():
    def __init__(self, history):
        self.fast = ExponentialMovingAverage(20)
        self.slow = ExponentialMovingAverage(100)
        self.macd = MovingAverageConvergenceDivergence(MACD_MA_FAST, MACD_MA_SLOW, MACD_MA_SIGNAL, MovingAverageType.Exponential)

        for bar in history.itertuples():
            self.fast.Update(bar.Index[1], bar.close)
            self.slow.Update(bar.Index[1], bar.close)
            self.macd.Update(bar.Index[1], bar.close)
            
    def is_ready(self):
        return self.fast.IsReady and self.slow.IsReady
        
    def update(self, time, price):
        self.fast.Update(time, price)
        self.slow.Update(time, price)
        self.macd.Update(time, price)
