#include "PositionManager.hpp"
#include <iomanip>
#include <cmath>

PositionManager::PositionManager(double balance) : accountBalance(balance) {}

bool PositionManager::openPosition(const Order& order, double fillPrice) {
    if (positions.find(order.ticker) != positions.end()) {
        std::cout << "[PositionManager] Warning: Position already exists for " << order.ticker << std::endl;
        return false;
    }

    Position pos;
    pos.ticker = order.ticker;
    pos.side = order.side;
    pos.entryPrice = fillPrice;
    pos.currentPrice = fillPrice;
    pos.lots = order.lots;
    pos.stopLoss = order.stopLoss;
    pos.takeProfit = order.takeProfit;
    pos.atrValue = 0.0; // Would be updated by market data
    pos.entryTime = std::chrono::system_clock::now();
    pos.highestPrice = fillPrice;
    pos.lowestPrice = fillPrice;
    pos.hrpWeight = 0.0; // Payload from Python

    positions[order.ticker] = pos;
    
    logTrade(order.ticker, "OPEN", fillPrice, 0.0, "Signal Execution");
    return true;
}

void PositionManager::updateMarketPrice(const std::string& ticker, double price) {
    if (positions.find(ticker) == positions.end()) return;

    auto& pos = positions[ticker];
    pos.currentPrice = price;

    // Update trailing stop bounds
    if (price > pos.highestPrice) pos.highestPrice = price;
    if (price < pos.lowestPrice) pos.lowestPrice = price;

    checkAutomatedExits(pos);
}

void PositionManager::checkAutomatedExits(Position& pos) {
    bool shouldClose = false;
    std::string reason = "";

    // 1. Stop Loss
    if (pos.side == Side::BUY && pos.currentPrice <= pos.stopLoss) {
        shouldClose = true; reason = "STOP_LOSS";
    } else if (pos.side == Side::SELL && pos.currentPrice >= pos.stopLoss) {
        shouldClose = true; reason = "STOP_LOSS";
    }

    // 2. Take Profit
    if (pos.side == Side::BUY && pos.currentPrice >= pos.takeProfit) {
        shouldClose = true; reason = "TAKE_PROFIT";
    } else if (pos.side == Side::SELL && pos.currentPrice <= pos.takeProfit) {
        shouldClose = true; reason = "TAKE_PROFIT";
    }

    if (shouldClose) {
        closePosition(pos.ticker, pos.currentPrice, reason);
    }
}

void PositionManager::closePosition(const std::string& ticker, double exitPrice, std::string reason) {
    if (positions.find(ticker) == positions.end()) return;

    auto pos = positions[ticker];
    double pnl = calculatePnL(pos);
    accountBalance += pnl;

    logTrade(ticker, "CLOSE", exitPrice, pnl, reason);
    positions.erase(ticker);
}

double PositionManager::calculatePnL(const Position& pos) const {
    double priceDiff = (pos.side == Side::BUY) ? (pos.currentPrice - pos.entryPrice) : (pos.entryPrice - pos.currentPrice);
    // Forex PnL = Diff * Lots * 100,000 (Standard Lot)
    return priceDiff * pos.lots * 100000.0;
}

double PositionManager::getPortfolioPnL() const {
    double total = 0;
    for (auto const& [ticker, pos] : positions) {
        total += calculatePnL(pos);
    }
    return total;
}

std::vector<Position> PositionManager::getActivePositions() const {
    std::vector<Position> active;
    for (auto const& [ticker, pos] : positions) {
        active.push_back(pos);
    }
    return active;
}

void PositionManager::logTrade(const std::string& ticker, const std::string& action, double price, double pnl, const std::string& reason) {
    std::cout << "[TRADE_EVENT] " << action << " | " << ticker 
              << " | Price: " << std::fixed << std::setprecision(5) << price 
              << " | PnL: $" << std::fixed << std::setprecision(2) << pnl 
              << " | Reason: " << reason << std::flush << std::endl;
}
