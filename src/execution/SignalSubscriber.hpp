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
    SignalSubscriber(ExecutionEngine* engine, const std::string& address = "tcp://127.0.0.1:5555") 
        : engine(engine), context(1), socket(context, ZMQ_PULL), last_sequence_id(0) {
        
        socket.connect(address);
        std::cout << "[C++] Connected to Hardened PUSH/PULL Bridge at " << address << std::endl;
    }

    void listen() {
        while (true) {
            zmq::message_t message;
            auto res = socket.recv(message, zmq::recv_flags::none);

            if (res) {
                std::string json_str(static_cast<char*>(message.data()), message.size());
                process_signals(json_str);
            }
        }
    }

private:
    void process_signals(const std::string& json_str) {
        try {
            auto j = nlohmann::json::parse(json_str);
            long current_seq = j["sequence_id"];
            
            // Gap Detection with Recovery Logging
            if (last_sequence_id != 0 && current_seq != last_sequence_id + 1) {
                long missed_count = current_seq - last_sequence_id - 1;
                std::cerr << "[C++] WARNING: Sequence Gap Detected!" << std::endl;
                std::cerr << "  Last received: " << last_sequence_id << std::endl;
                std::cerr << "  Current packet: " << current_seq << std::endl;
                std::cerr << "  Missed packets: " << missed_count << std::endl;
                std::cerr << "[C++] Initiating recovery: missing signals may need retransmission" << std::endl;
                
                // Log gap event for monitoring/alerting
                log_sequence_gap(last_sequence_id, current_seq);
            }
            last_sequence_id = current_seq;

            std::cout << "[C++] Received Packet #" << current_seq << " with " << j["count"] << " tickets" << std::endl;
            
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
            std::cerr << "[C++] CRITICAL: Error parsing signals: " << e.what() << std::endl;
            log_parse_error(json_str, e.what());
        }
    }

    void log_sequence_gap(long last_seq, long current_seq) {
        // Log gap for retry mechanism or alerting
        // In production, this could trigger a request back to Python for re-transmission
        std::string gap_log = "[SEQ_GAP] last=" + std::to_string(last_seq) + 
                             " current=" + std::to_string(current_seq);
        std::cerr << gap_log << std::endl;
    }

    void log_parse_error(const std::string& json_str, const std::string& error) {
        // Log failed JSON parse for debugging
        std::string truncated = json_str.length() > 100 ? json_str.substr(0, 100) + "..." : json_str;
        std::string error_log = "[PARSE_ERR] " + error + " | payload=" + truncated;
        std::cerr << error_log << std::endl;
    }

    ExecutionEngine* engine;
    zmq::context_t context;
    zmq::socket_t socket;
    long last_sequence_id;
};
