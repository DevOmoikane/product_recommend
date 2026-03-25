import logging

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

from ml_library.utils.plugins import load_plugins
from ml_library.model.regression import ModelRegression, ModelRegressionRegistry
from ml_library.model.recommendation import ModelRecommendationRegistry


if __name__ == "__main__":
    load_plugins("ml_library.model.regression_models")
    load_plugins("ml_library.model.recommendation_models")

    print("Available regression models:", ModelRegressionRegistry.available())

    print("Available recommendation models:", ModelRecommendationRegistry.available())
    
    model = ModelRegressionRegistry.create("gbr", n_estimators=100, learning_rate=0.1)
    print(f"Created model: {model.friendly_name}")
    model.save_model("models/gbr_model.joblib")

    # model = ModelRecommendationRegistry.create("als")

    model_instance, model_variables = ModelRegression.load_model("models/gbr_model.joblib")
    # friendly name is in the first class from the mro of the loaded model, so we can check if it is loaded correctly
    first_class = model_instance.__class__.mro()[0]
    friendly_name = first_class.__dict__.get("_friendly_name", "N/A")
    class_name = first_class.__name__
    print(f"Loaded model class: {class_name}, friendly name: {friendly_name}")
