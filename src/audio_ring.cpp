#include "catchall/audio_ring.hpp"

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
        return size_;
    }

    std::uint64_t AudioRing::dropped_samples() const noexcept {
        return dropped_samples_;
    }

    void AudioRing::write(std::span<const float> samples) {
        for (const float sample : samples) {
            buffer_[write_position_] = sample;
            write_position_ = (write_position_ + 1) % capacity();

            if (size_ == capacity()) {
                read_position_ = (read_position_ + 1) % capacity();
                ++dropped_samples_;
            } else {
                ++size_;
            }
        }
    }

    bool AudioRing::read(std::span<float> destination) {
        if (destination.size() > size_) {
            return false;
        }

        for (float& sample : destination) {
            sample = buffer_[read_position_];
            read_position_ = (read_position_ + 1) % capacity();
        }

        size_ -= destination.size();
        return true;
    }
}