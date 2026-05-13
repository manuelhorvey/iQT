#pragma once

#include "Order.h"
#include <vector>
#include <map>
#include <iostream>
#include <random>

class ExecutionEngine {
public:
    ExecutionEngine() : gen(rd()), dis(0.1, 0.5) {} // 0.1 - 0.5 pips slippage simulation

    void on_signal(const std::string& ticker, const std::string& side_str, double lots, double price, double sl, double tp) {
        std::cout << "[Engine] Processing signal for " << ticker << "..." << std::endl;

        Side side = (side_str == "BUY") ? Side::BUY : Side::SELL;
        
        // 1. Create Order
        Order new_order;
        new_order.id = "ORD_" + std::to_string(order_counter++);
        new_order.ticker = ticker;
        new_order.side = side;
        new_order.type = OrderType::MARKET;
        new_order.quantity = lots;
        new_order.price = price;
        new_order.stop_loss = sl;
        new_order.take_profit = tp;
        new_order.timestamp = std::chrono::system_clock::now();

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

        std::cout << "[Engine] Order " << order.id << " FILLED" << std::endl;
        std::cout << "  -> Ticker: " << order.ticker << " | Lots: " << order.quantity << std::endl;
        std::cout << "  -> Entry: " << order.price << " | Filled: " << filled_price << std::endl;
        std::cout << "  -> Slippage: " << slippage_pips << " pips" << std::endl;

        // 3. Update Position Manager
        Position& pos = positions[order.ticker];
        pos.ticker = order.ticker;
        pos.side = order.side;
        pos.quantity = order.quantity;
        pos.entry_price = filled_price;
        pos.is_active = true;

        std::cout << "[Engine] Position Updated for " << order.ticker << std::endl;
        std::cout << "------------------------------------------" << std::endl;
    }

    int order_counter = 1000;
    std::map<std::string, Position> positions;
    
    // Simulation randomness
    std::random_device rd;
    std::mt19937 gen;
    std::uniform_real_distribution<> dis;
};
