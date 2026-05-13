#pragma once

#include <string>
#include <chrono>

enum class Side { BUY, SELL, NONE };
enum class OrderType { MARKET, LIMIT, STOP };
enum class OrderStatus { NEW, FILLED, CANCELLED, REJECTED };

struct Order {
    std::string id;
    std::string ticker;
    Side side;
    OrderType type;
    double quantity; // Lots
    double price;    // Entry Price
    double stop_loss;
    double take_profit;
    std::chrono::system_clock::time_point timestamp;
};

struct Position {
    std::string ticker;
    Side side;
    double quantity;
    double entry_price;
    double current_price;
    double unrealized_pnl;
    bool is_active = false;

    void update_pnl(double market_price) {
        current_price = market_price;
        double multiplier = (side == Side::BUY) ? 1.0 : -1.0;
        // Forex PnL: (Price_Diff) * Lots * 100,000
        unrealized_pnl = (current_price - entry_price) * quantity * 100000.0 * multiplier;
    }
};

struct ExecutionReport {
    std::string order_id;
    OrderStatus status;
    double filled_price;
    double slippage_pips;
};
