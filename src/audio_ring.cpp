#include "catchall/audio_ring.hpp"

#include <algorithm>
#include <stdexcept>

namespace catchall {
    AudioRing::AudioRing(std::size_t capacity)
        : buffer_(capacity) {
            if (capacity == 0) {
                throw std::invalid_argument("AudioRing capacity must be greater than zero");
            }
        }

    std::size_t AudioRing::capacity() const noexcept {
        return buffer_.size();
    }

    std::size_t AudioRing::size() const noexcept {
        const std::uint64_t read = read_index_.load(std::memory_order_acquire);
        const std::uint64_t write = write_index_.load(std::memory_order_acquire);

        return static_cast<std::size_t>(write - read);
    }

    std::uint64_t AudioRing::dropped_samples() const noexcept {
        return dropped_samples_.load(std::memory_order_relaxed);
    }

    std::size_t AudioRing::write(std::span<const float> samples) noexcept {
        const std::uint64_t write = write_index_.load(std::memory_order_relaxed);
        const std::uint64_t read = read_index_.load(std::memory_order_acquire);

        const std::size_t used = static_cast<std::size_t>(write - read);
        const std::size_t free = capacity() - used;
        const std::size_t accepted = std::min(samples.size(), free);

        for (std::size_t index = 0; index < accepted; ++index) {
            buffer_[(write + index) % capacity()] = samples[index];
        }

        write_index_.store(write + accepted, std::memory_order_release);

        const std::size_t dropped = samples.size() - accepted;
        dropped_samples_.fetch_add(dropped, std::memory_order_relaxed);

        return accepted;
    }

    bool AudioRing::read(std::span<float> destination) noexcept {
        const std::uint64_t read = read_index_.load(std::memory_order_relaxed);
        const std::uint64_t write = write_index_.load(std::memory_order_acquire);

        const std::size_t available = static_cast<std::size_t>(write - read);

        if (destination.size() > available) {
            return false;
        }

        for (std::size_t index = 0; index < destination.size(); ++index) {
            destination[index] = buffer_[(read + index) % capacity()];
        }

        read_index_.store(
            read + destination.size(),
            std::memory_order_release
        );

        return true;
    }
}