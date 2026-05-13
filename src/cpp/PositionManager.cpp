#include "PositionManager.hpp"
#include <iomanip>
#include <cmath>
#include <fstream>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

PositionManager::PositionManager(double balance) : accountBalance(balance) {
    loadState(); // Try to recover previous state on startup
}

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
    saveState(); // Persist immediately
    return true;
}

void PositionManager::saveState(const std::string& filename) {
    json j;
    j["accountBalance"] = accountBalance;
    j["positions"] = json::array();

    for (auto const& [ticker, pos] : positions) {
        json p;
        p["ticker"] = pos.ticker;
        p["side"] = (pos.side == Side::BUY) ? "BUY" : "SELL";
        p["entryPrice"] = pos.entryPrice;
        p["currentPrice"] = pos.currentPrice;
        p["lots"] = pos.lots;
        p["stopLoss"] = pos.stopLoss;
        p["takeProfit"] = pos.takeProfit;
        p["highestPrice"] = pos.highestPrice;
        p["lowestPrice"] = pos.lowestPrice;
        p["entryTime"] = std::chrono::system_clock::to_time_t(pos.entryTime);
        j["positions"].push_back(p);
    }

    std::ofstream file(filename);
    if (file.is_open()) {
        file << j.dump(4);
        // std::cout << "[PositionManager] State persisted to " << filename << std::endl;
    }
}

void PositionManager::loadState(const std::string& filename) {
    std::ifstream file(filename);
    if (!file.is_open()) return;

    try {
        json j;
        file >> j;
        accountBalance = j["accountBalance"];
        
        for (const auto& p : j["positions"]) {
            Position pos;
            pos.ticker = p["ticker"];
            pos.side = (p["side"] == "BUY") ? Side::BUY : Side::SELL;
            pos.entryPrice = p["entryPrice"];
            pos.currentPrice = p["currentPrice"];
            pos.lots = p["lots"];
            pos.stopLoss = p["stopLoss"];
            pos.takeProfit = p["takeProfit"];
            pos.highestPrice = p["highestPrice"];
            pos.lowestPrice = p["lowestPrice"];
            pos.entryTime = std::chrono::system_clock::from_time_t(p["entryTime"]);
            
            positions[pos.ticker] = pos;
        }
        std::cout << "[PositionManager] Successfully recovered " << positions.size() << " positions from " << filename << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[PositionManager] Failed to load state: " << e.what() << std::endl;
    }
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

    // 1. Hard Stop Loss
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

    // 3. Dynamic Trailing Stop & Break-Even (Institutional Protection)
    double slDistance = std::abs(pos.entryPrice - pos.stopLoss);
    double entryToStopPips = std::abs(pos.entryPrice - pos.stopLoss); // Original risk
    
    if (pos.side == Side::BUY) {
        double currentProfit = pos.currentPrice - pos.entryPrice;
        
        // Break-Even Logic: If up by 1.0 ATR equivalent (estimated from SL)
        // Move SL to entry
        if (currentProfit > (entryToStopPips * 0.5) && pos.stopLoss < pos.entryPrice) {
            pos.stopLoss = pos.entryPrice;
            std::cout << "[PositionManager] Break-Even: SL moved to entry for " << pos.ticker << std::endl;
            saveState();
        }

        // Trailing Stop Logic
        if (currentProfit > slDistance) {
            double newStop = pos.highestPrice - slDistance;
            if (newStop > pos.stopLoss) {
                pos.stopLoss = newStop;
                saveState(); // Update persistent SL
            }
        }
    } else {
        double currentProfit = pos.entryPrice - pos.currentPrice;

        // Break-Even Logic
        if (currentProfit > (entryToStopPips * 0.5) && pos.stopLoss > pos.entryPrice) {
            pos.stopLoss = pos.entryPrice;
            std::cout << "[PositionManager] Break-Even: SL moved to entry for " << pos.ticker << std::endl;
            saveState();
        }

        if (currentProfit > slDistance) {
            double newStop = pos.lowestPrice + slDistance;
            if (newStop < pos.stopLoss) {
                pos.stopLoss = newStop;
                saveState();
            }
        }
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
    saveState(); // Update state after closure
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
