#pragma once

#include "Order.h"
#include "PositionManager.hpp"
#include <vector>
#include <map>
#include <iostream>
#include <random>

class ExecutionEngine {
public:
    ExecutionEngine() : posManager(100000.0), gen(rd()), dis(0.1, 0.5) {} 

    void on_signal(const std::string& ticker, const std::string& side_str, double lots, double price, double sl, double tp) {
        std::cout << "[Engine] Processing signal for " << ticker << "..." << std::endl;

        Side side = (side_str == "BUY") ? Side::BUY : Side::SELL;
        
        // 1. Create Order
        Order new_order;
        new_order.ticker = ticker;
        new_order.side = side;
        new_order.type = OrderType::MARKET;
        new_order.lots = lots;
        new_order.price = price;
        new_order.stopLoss = sl;
        new_order.takeProfit = tp;

        // 2. Simulate Fill (Forex Simulation)
        execute_simulated_fill(new_order);
    }

private:
    void execute_simulated_fill(const Order& order) {
        // Stochastic Slippage Calculation
        double slippage_pips = dis(gen);
        double pip_value = (order.ticker.find("JPY") != std::string::npos) ? 0.01 : 0.0001;
        double slippage_price = slippage_pips * pip_value;

        double filled_price = (order.side == Side::BUY) ? order.price + slippage_price : order.price - slippage_price;

        std::cout << "[Engine] Order for " << order.ticker << " FILLED" << std::endl;
        std::cout << "  -> Lots: " << order.lots << " | Filled: " << filled_price << std::endl;

        // 3. Update Position Manager
        posManager.openPosition(order, filled_price);
    }

    PositionManager posManager;
    
    // Simulation randomness
    std::random_device rd;
    std::mt19937 gen;
    std::uniform_real_distribution<> dis;
};
