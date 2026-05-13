#ifndef MARKET_DATA_FEED_H
#define MARKET_DATA_FEED_H

#include <string>
#include <vector>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <atomic>

struct Tick {
    std::string symbol;
    double price;
    long long timestamp;
};

class MarketDataFeed {
public:
    MarketDataFeed() : running(false) {}
    ~MarketDataFeed() { stop(); }

    void start() {
        running = true;
        feed_thread = std::thread(&MarketDataFeed::run, this);
    }

    void stop() {
        running = false;
        if (feed_thread.joinable()) feed_thread.join();
    }

    void subscribe(const std::string& symbol) {
        symbols.push_back(symbol);
    }

    bool get_next_tick(Tick& tick) {
        std::unique_lock<std::mutex> lock(mtx);
        if (tick_queue.empty()) {
            return false;
        }
        tick = tick_queue.front();
        tick_queue.pop();
        return true;
    }

private:
    void run() {
        // Simulated low-latency feed
        while (running) {
            for (const auto& symbol : symbols) {
                Tick t = { symbol, 100.0 + (rand() % 1000) / 100.0, 123456789 }; // Dummy data
                {
                    std::lock_guard<std::mutex> lock(mtx);
                    tick_queue.push(t);
                }
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100)); // 10Hz feed
        }
    }

    std::vector<std::string> symbols;
    std::queue<Tick> tick_queue;
    std::mutex mtx;
    std::thread feed_thread;
    std::atomic<bool> running;
};

#endif
