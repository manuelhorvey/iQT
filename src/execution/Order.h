#pragma once
#include <string>
#include <chrono>

/**
 * @brief Institutional Order and Position primitives.
 */

enum class Side { BUY, SELL, NONE };
enum class OrderType { MARKET, LIMIT, STOP };
enum class OrderStatus { NEW, FILLED, CANCELLED, REJECTED };

struct Order {
    std::string id;
    std::string ticker;
    Side side;
    OrderType type;
    double lots;      // Standard Lots (100k units)
    double price;     // Target/Execution Price
    double stopLoss;
    double takeProfit;
    std::chrono::system_clock::time_point timestamp;
};

struct ExecutionReport {
    std::string order_id;
    OrderStatus status;
    double filled_price;
    double slippage_pips;
};
