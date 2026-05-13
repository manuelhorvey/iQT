#pragma once
#include <unordered_map>
#include <string>
#include <vector>
#include <chrono>
#include <iostream>
#include "Order.h"

/**
 * @brief Represents an active market commitment.
 */
struct Position {
    std::string ticker;
    Side side;                    
    double entryPrice;
    double currentPrice;
    double lots;
    double stopLoss;
    double takeProfit;           
    double atrValue;
    std::chrono::system_clock::time_point entryTime;
    double highestPrice;          // For trailing stop
    double lowestPrice;           // For trailing stop
    double hrpWeight;             
};

/**
 * @brief Institutional Position & Risk Manager.
 * Handles real-time monitoring and automated exits (SL/TP/Trail).
 */
class PositionManager {
public:
    PositionManager(double accountBalance = 100000.0);
    
    // Core Actions
    bool openPosition(const Order& order, double fillPrice);
    void updateMarketPrice(const std::string& ticker, double currentPrice);
    void closePosition(const std::string& ticker, double exitPrice, std::string reason = "Manual");
    
    // Analytics
    double getPortfolioPnL() const;
    double getEquity() const { return accountBalance + getPortfolioPnL(); }
    std::vector<Position> getActivePositions() const;

private:
    std::unordered_map<std::string, Position> positions;
    double accountBalance;
    double riskPerTradePct = 0.005; 
    
    // Internal Logic
    void checkAutomatedExits(Position& pos);
    double calculatePnL(const Position& pos) const;
    void logTrade(const std::string& ticker, const std::string& action, double price, double pnl, const std::string& reason);
};
