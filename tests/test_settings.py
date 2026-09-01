from catchall.settings import RecognitionSettings


def test_recognition_settings_have_local_defaults() -> None:
    assert RecognitionSettings.from_environment({}) == RecognitionSettings(
        model_name="tiny.en",
        device="cpu",
        compute_type="int8",
    )


def test_recognition_settings_read_environment() -> None:
    settings = RecognitionSettings.from_environment(
        {
            "CATCHALL_WHISPER_MODEL": "base.en",
            "CATCHALL_WHISPER_DEVICE": "cpu",
            "CATCHALL_WHISPER_COMPUTE_TYPE": "int8",
        }
    )

    assert settings.model_name == "base.en"
    assert settings.device == "cpu"
    assert settings.compute_type == "int8"