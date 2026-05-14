#include "SignalSubscriber.hpp"
#include "ExecutionEngine.hpp"
#include <csignal>

/**
 * @brief Institutional C++ Execution Engine - Main Entry Point.
 * 
 * Orchestrates the ZeroMQ Signal Bridge and the Execution Engine simulation.
 */

// Global flag for clean shutdown
bool keep_running = true;
void signal_handler(int signal) {
    std::cout << "\n[C++] Shutting down execution engine..." << std::endl;
    keep_running = false;
    exit(0);
}

int main() {
    std::signal(SIGINT, signal_handler);

    std::cout << "==========================================" << std::endl;
    std::cout << " INSTITUTIONAL FOREX EXECUTION ENGINE " << std::endl;
    std::cout << "==========================================" << std::endl;

    // 1. Initialize Execution Engine (Simulation Mode)
    ExecutionEngine engine;

    // 2. Initialize Signal Bridge (Subscriber)
    SignalSubscriber subscriber(&engine);

    // 3. Start Listening for Python Signals
    std::cout << "[C++] Engine ready. Waiting for signals from Python..." << std::endl;
    
    try {
        subscriber.listen();
    } catch (const std::exception& e) {
        std::cerr << "[C++] Fatal Runtime Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
