#include "catchall/audio_ring.hpp"

#include <array>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include <string>
#include <atomic>
#include <thread>

namespace {
    void expect(bool condition, std::string_view message) {
        if (!condition) {
            throw std::runtime_error(std::string(message));
        }
    }

    void test_rejects_zero_capacity() {
        bool threw = false;

        try {
            catchall::AudioRing ring(0);
        } catch (const std::invalid_argument&) {
            threw = true;
        }

        expect(threw, "zero capacity should be rejected");
    }

    void test_write_and_read_round_trip() {
        catchall::AudioRing ring(4);

        const std::array<float, 3> input{1.0F, 2.0F, 3.0F};
        std::array<float, 3> output{};

        expect(
            ring.write(input) == input.size(),
            "all samples should be accepted"
        );

        expect(ring.size() == 3, "three samples should be available");
        expect(ring.read(output), "three samples should be readable");
        expect(output == input, "read samples should match written samples");
        expect(ring.size() == 0, "reading should consume the samples");
    }

    void test_wraps_around() {
        catchall::AudioRing ring(4);

        const std::array<float, 3> first{1.0F, 2.0F, 3.0F};
        std::array<float, 2> consumed{};

        expect(
            ring.write(first) == first.size(),
            "the first write should be accepted"
        );
        expect(ring.read(consumed), "initial samples should be readable");

        const std::array<float, 3> second{4.0F, 5.0F, 6.0F};
        std::array<float, 4> output{};

        expect(
            ring.write(second) == second.size(),
            "the second write should be accepted"
        );

        expect(ring.read(output), "wrapped samples should be readable");
        expect(
            output == std::array<float, 4> {3.0F, 4.0F, 5.0F, 6.0F},
            "wrapping should preserve FIFO order"
        );
    }

    void test_overflow_rejects_new_samples() {
        catchall::AudioRing ring(3);

        const std::array<float, 5> input{1.0F, 2.0F, 3.0F, 4.0F, 5.0F};
        std::array<float, 3> output{};

        const std::size_t accepted = ring.write(input);

        expect(accepted == 3, "only free capacity should be accepted");
        expect(ring.size() == 3, "size should not exceed capacity");
        expect(ring.dropped_samples() == 2, "rejected samples should be counted");
        expect(ring.read(output), "accepted samples should be readable");
        expect(
            output == std::array<float, 3>{1.0F, 2.0F, 3.0F},
            "overflow should preserve existing unread samples"
        );
    }

    void test_failed_read_does_not_consume_samples() {
        catchall::AudioRing ring(4);

        const std::array<float, 2> input{1.0F, 2.0F};
        std::array<float, 3> too_large{};
        std::array<float, 2> output{};

        expect(
            ring.write(input) == input.size(),
            "all samples should be accepted"
        );

        expect(!ring.read(too_large), "an oversized read should fail");
        expect(ring.size() == 2, "a failed read should not consume samples");
        expect(ring.read(output), "the original samples should remain readable");
        expect(output == input, "failed reads should not alter buffered data");
    }

    void test_write_uses_remaining_capacity() {
        catchall::AudioRing ring(4);

        const std::array<float, 3> first{1.0F, 2.0F, 3.0F};
        const std::array<float, 3> second{4.0F, 5.0F, 6.0F};
        std::array<float, 4> output{};

        expect(ring.write(first) == 3, "the first write should fit");
        expect(ring.write(second) == 1, "only one remaininig slot should be used");
        expect(ring.dropped_samples() == 2, "the other two samples should be dropped");
        expect(ring.read(output), "the full buffer should be readable");
        expect(
            output == std::array<float, 4>{1.0F, 2.0F, 3.0F, 4.0F},
            "a partial write should preserve FIFO order"
        );
    }

    void test_concurrent_producer_consumer() {
        constexpr std::size_t total_samples = 100'000;

        catchall::AudioRing ring(256);
        std::atomic<bool> correct{true};

        std::thread producer([&ring] () {
            for (std::size_t value=0; value < total_samples; ++value) {
                const std::array<float, 1> sample{
                    static_cast<float>(value)
                };
                
                while (ring.write(sample) == 0) {
                    std::this_thread::yield();
                }
            }
        });

        std::thread consumer([&ring, &correct] () {
            std::size_t expected = 0;

            while (expected < total_samples) {
                std::array<float, 1> sample{};
                
                if (!ring.read(sample)) {
                    std::this_thread::yield();
                    continue;
                }

                if (sample[0] != static_cast<float>(expected)) {
                    correct.store(false, std::memory_order_relaxed);
                }

                ++expected;
            }
        });

        producer.join();
        consumer.join();

        expect(correct.load(), "concurrent samples should remain in FIFO order");
        expect(ring.size() == 0, "the consumer should drain the ring");
    }

}

int main() {
    try {
        test_rejects_zero_capacity();
        test_write_and_read_round_trip();
        test_wraps_around();
        test_overflow_rejects_new_samples();
        test_failed_read_does_not_consume_samples();
        test_write_uses_remaining_capacity();
        test_concurrent_producer_consumer();
    } catch (const std::exception& error) {
        std::cerr << "FAILED: " << error.what() << '\n';
        return 1;
    }

    std::cout << "All audio ring tests passed.\n";
    return 0;
}