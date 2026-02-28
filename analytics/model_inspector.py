import json
import pickle
import math

with open('1ModelK.pkl', 'rb') as f:
    model = pickle.load(f)

coef = model.coef_[0][0]
intercept = model.intercept_[0]

x_values = [0, 0.1, 0.5, 0.9]
calculations = {}

for x in x_values:
    z = (coef * x) + intercept
    probability_class_1 = 1 / (1 + math.exp(-z))

    calculations[f"x={x}"] = {
        "logit_score_z": z,
        "prob_class_1": probability_class_1,
        "predicted_class": int(probability_class_1 >= 0.5)
    }

params = {
    "coefficients": model.coef_.tolist(),
    "intercept": model.intercept_.tolist(),
    "classes": model.classes_.tolist(),
    "solver": "liblinear",
    "test_calculations": calculations
}

with open("model_parameters.json", "w") as f:
    json.dump(params, f, indent=4)
