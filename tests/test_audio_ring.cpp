#include "catchall/audio_ring.hpp"

#include <array>
#include <iostream>
#include <stdexcept>
#include <string_view>

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

        ring.write(input);

        expect(ring.size() == 3, "three samples should be available");
        expect(ring.read(output), "three samplse should be readable");
        expect(output == input, "read samples should match written samples");
        expect(ring.size() == 0, "reading should consume the samples");
    }

    void test_wraps_around() {
        catchall::AudioRing ring(4);

        const std:: array<float, 3> first{1.0F, 2.0F, 3.0F};
        std::array<float, 2> consumed{};

        ring.write(first);
        expect(ring.read(consumed), "initial samples should be readable");

        const std::array<float, 3> second{4.0F, 5.0F, 6.0F};
        std::array<float, 4> output{};

        ring.write(second);

        expect(ring.read(output), "wrapped samples should be readable");
        expect(
            output == std::array<float, 4> {3.0F, 4.0F, 5.0F, 6.0F},
            "wrapping should preserve FIFO order"
        );
    }

    void test_overflow_keeps_newest_samples() {
        catchall::AudioRing ring(3);

        const std::array<float, 5> input{1.0F, 2.0F, 3.0F, 4.0F, 5.0F};
        std::array<float, 3> output{};

        ring.write(input);

        expect(ring.size() == 3, "size should not exceed capacity");
        expect(ring.dropped_samples() == 2, "two overwritten samples should be counted");
        expect(ring.read(output), "remaining samples should be readable");
        expect(
            output == std::array<float, 3>{3.0F, 4.0F, 5.0F},
            "overflow should retain the newest samples"
        );
    }

    void test_failed_read_does_not_consume_samples() {
        catchall::AudioRing ring(4);

        const std::array<float, 2> input{1.0F, 2.0F};
        std::array<float, 3> too_large{};
        std::array<float, 2> output{};

        ring.write(input);

        expect(!ring.read(too_large), "an oversized read should fail");
        expect(ring.size() == 2, "a failed read should not consume samples");
        expect(ring.read(output), "the original samples should remain readable");
        expect(output == input, "failed reads should not alter buffered data");
    }

}

int main() {
    try {
        test_rejects_zero_capacity();
        test_write_and_read_round_trip();
        test_wraps_around();
        test_overflow_keeps_newest_samples();
        test_failed_read_does_not_consume_samples();
    } catch (const std::exception& error) {
        std::cerr << "FAILED: " << error.what() << '\n';
        return 1;
    }

    std::cout << "All audio ring tests passed. \n";
    return 0;
}