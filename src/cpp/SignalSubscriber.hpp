#pragma once

#include <zmq.hpp>
#include <string>
#include <iostream>
#include <nlohmann/json.hpp>

/**
 * @brief Professional ZeroMQ Signal Subscriber for the C++ Execution Engine.
 * 
 * This class listens for "trading.signals" topics from the Python research layer
 * and deserializes the JSON payload for the execution logic.
 */
#include "ExecutionEngine.hpp"

class SignalSubscriber {
public:
    SignalSubscriber(ExecutionEngine* engine, const std::string& address = "tcp://localhost:5555") 
        : engine(engine), context(1), socket(context, ZMQ_SUB) {
        
        socket.connect(address);
        socket.setsockopt(ZMQ_SUBSCRIBE, "trading.signals", 15);
        std::cout << "[C++] Connected to Python Signal Bridge at " << address << std::endl;
    }

    void listen() {
        while (true) {
            zmq::message_t topic;
            zmq::message_t payload;

            auto res_topic = socket.recv(topic, zmq::recv_flags::none);
            auto res_payload = socket.recv(payload, zmq::recv_flags::none);

            if (res_payload) {
                std::string json_str(static_cast<char*>(payload.data()), payload.size());
                process_signals(json_str);
            }
        }
    }

private:
    void process_signals(const std::string& json_str) {
        try {
            auto j = nlohmann::json::parse(json_str);
            std::cout << "[C++] Received " << j["count"] << " tickets at " << j["timestamp"] << std::endl;
            
            for (const auto& ticket : j["tickets"]) {
                engine->on_signal(
                    ticket["ticker"], 
                    ticket["signal"], 
                    ticket["lots"], 
                    ticket["price"], 
                    ticket["stop_loss"], 
                    ticket["take_profit"]
                );
            }
        } catch (const std::exception& e) {
            std::cerr << "[C++] Error parsing signals: " << e.what() << std::endl;
        }
    }

    ExecutionEngine* engine;
    zmq::context_t context;
    zmq::socket_t socket;
};
