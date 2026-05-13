#include <iostream>
#include <chrono>
#include <thread>
#include "MarketDataFeed.h"

class ExecutionEngine {
public:
    void execute_order(const std::string& symbol, double price, int quantity, const std::string& side) {
        std::cout << "[EXECUTION] " << side << " " << quantity << " units of " << symbol 
                  << " at $" << price << std::endl;
    }
};

int main() {
    std::cout << "==========================================" << std::endl;
    std::cout << "Institutional Quant Trader C++ Engine" << std::endl;
    std::cout << "==========================================" << std::endl;

    MarketDataFeed feed;
    ExecutionEngine execution;

    feed.subscribe("BTC-USD");
    feed.subscribe("ETH-USD");
    feed.start();

    std::cout << "[SYSTEM] Market data feed started..." << std::endl;

    // Run for a short period to demonstrate tick ingestion
    auto start_time = std::chrono::steady_clock::now();
    while (std::chrono::steady_clock::now() - start_time < std::chrono::seconds(5)) {
        Tick tick;
        if (feed.get_next_tick(tick)) {
            std::cout << "[TICK] " << tick.symbol << " : $" << tick.price << std::endl;
            
            // Simple threshold-based execution logic for demonstration
            if (tick.price > 105.0) {
                execution.execute_order(tick.symbol, tick.price, 100, "SELL");
            } else if (tick.price < 101.0) {
                execution.execute_order(tick.symbol, tick.price, 100, "BUY");
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }

    feed.stop();
    std::cout << "==========================================" << std::endl;
    std::cout << "Engine Shutdown Cleanly." << std::endl;
    std::cout << "==========================================" << std::endl;

    return 0;
}
