# 0 to Hero: DDoS ML Model Overview

This document provides a comprehensive analysis of the Machine Learning model used for DDoS detection in the IoT Project.

## 1. Introduction
The core of the security system is a **Deep Learning binary classifier** designed to detect Distributed Denial of Service (DDoS) attacks in real-time. It operates within the `MLSecurityEngine` and works in tandem with a heuristic-based fallback system (`SimpleDDoSDetector`).

## 2. Model Architecture
The model is a **Feed-Forward Neural Network (Sequential)** built using **Keras/TensorFlow**. It is designed to classify network packets as either "Normal" or "Attack".

### Network Structure
| Layer Type | Units / Parameters | Activation | Description |
|------------|-------------------|------------|-------------|
| **Input** | 77 Features | - | Input vector representing traffic features |
| **Dense** | 128 Neurons | ReLU | First hidden layer for feature extraction |
| **Dropout** | Rate: 0.3 | - | Prevents overfitting by randomly dropping 30% connections |
| **Dense** | 64 Neurons | ReLU | Second hidden layer |
| **Dropout** | Rate: 0.3 | - | Dropout regularization |
| **Dense** | 32 Neurons | ReLU | Third hidden layer |
| **Dropout** | Rate: 0.2 | - | Dropout regularization |
| **Output** | 1 Neuron | Sigmoid | Outputs probability (0.0 to 1.0) |

-   **Optimizer**: Adam (Learning Rate: 0.001)
-   **Loss Function**: Binary Crossentropy (Standard for binary classification)
-   **Metrics**: Accuracy

## 3. Training Data & Source
The model appears to be trained on the **CIC-DDoS2019** dataset, a benchmark dataset for DDoS attacks.
-   **Evidence**: The presence of `models/robust_cic_ddos2019_model_20251008-125914.h5` strongly indicates this lineage.
-   **Scope**: The dataset typically includes common DDoS attacks like TCP Flood, UDP Flood, HTTP Flood, and Smurf attacks.

## 4. Feature Engineering
The model requires a specific input vector of **77 features**. These features are extracted or derived from raw packet data in `MLSecurityEngine.extract_features`.

### Feature Categories
1.  **Basic Protocol Headers (15 features)**:
    -   `packet_size`, `protocol`, `src_port`, `dst_port`, `tcp_flags`, `ttl`, `window_size`, etc.
2.  **Statistical Derived Features (20 features)**:
    -   Ratios like `packet_size / 1500` (MTU), `size * rate`, `size / pps`.
3.  **Rate-Based Features (5 features)**:
    -   Normalized packet rates, byte rates (BPS), and PPS.
4.  **Protocol-Specific Normalizations (5 features)**:
    -   Normalized Protocol ID, TCP flags, Window size.
5.  **Port Analysis (5 features)**:
    -   Normalized source/dest ports, port differences (detects port scanning patterns).
6.  **Timing Analysis (5 features)**:
    -   Connection duration, Duration per packet, etc.
7.  **Attack Indicators (5 features)**:
    -   Binary flags for high rates (>1000 PPS), large packets, SYN flags (SYN Flood indicator).
8.  **Padding/Derived (Remainder)**:
    -   Additional derived values to ensure the vector length is exactly 77, matching the training input shape.

## 5. System Integration

### Core Components
-   **`ml_security_engine.py`**: The main orchestrator.
    -   Loads the model from `data/models/ddos_model_retrained`.
    -   Implements `extract_features()` to transform raw packets into the 77-feature vector.
    -   Runs inference (`model.predict()`).
    -   Categorizes attacks based on confidence:
        -   **> 90%**: Confirmed DDoS Attack
        -   **> 70%**: Volume Attack
        -   **> 50%**: Rate Attack
-   **`simple_ddos_detector.py`**: A heuristic fallback.
    -   Used if TensorFlow is unavailable or the ML model fails to load.
    -   Also combined with ML output for a "Hybrid" score (70% ML + 30% Simple).
    -   Checks simple thresholds (e.g., PPS > 1000, BPS > 10MB/s).

### Logic Flow
1.  **Packet Arrives**: Network monitor captures a packet artifact.
2.  **Feature Extraction**: `ml_engine.extract_features(packet)` converts it to a (1, 77) numpy array.
3.  **Inference**: `model.predict()` returns a confidence score (0.0 - 1.0).
4.  **Classification**:
    -   If Confidence > 0.5 -> **Attack**.
    -   Specific type determined by confidence level and heuristic checks.
5.  **Action**:
    -   Update Dashboard Statistics.
    -   Log Alert.
    -   Block IP (if configured).

## 6. Directory Map
-   **Engine**: `d:/Projects/Research/iot/IOT-project/ml_security_engine.py`
-   **Heuristics**: `d:/Projects/Research/iot/IOT-project/simple_ddos_detector.py`
-   **Active Model**: `d:/Projects/Research/iot/IOT-project/data/models/ddos_model_retrained/`
    -   `config.json`: Architecture definition.
    -   `model.weights.h5`: Trained weights.
-   **Backup/Source Models**: `d:/Projects/Research/iot/IOT-project/models/`

## 7. How to Use / Retrain
Since no training script is present in the repository, the model operates in **Inference Mode** only.
To retrain:
1.  You would need the original CIC-DDoS2019 CSV dataset.
2.  Create a script to load CSVs, preprocess columns to match the 77 features.
3.  Use `keras.Sequential` to rebuild the architecture described in Section 2.
4.  Train with `model.fit()` and save using `model.save('data/models/ddos_model_retrained')`.

## 8. Beginner's Guide: ML & Reinforcement Learning 101

### What is Machine Learning (ML)?
Machine Learning is a subset of AI where computers learn from data without being explicitly programmed for every specific rule.
-   **Traditional Programming**: Rules + Data = Answers.
-   **Machine Learning**: Data + Answers = Rules.

In this project, we use **Supervised Learning**. We showed the model millions of examples of "Normal Traffic" and "DDoS Attacks" during training. It "learned" the patterns (the Rules) that distinguish them. Now, when it sees new traffic, it applies those rules to predict if it's an attack.

### What is Deep Learning?
Deep Learning is a specialized type of ML inspired by the human brain. It uses **Neural Networks** with many layers (hence "Deep").
-   **Our Model**: Uses a "Dense" neural network.
-   **How it works**: Data passes through layers of "neurons". Each neuron performs a tiny mathematical calculation. By combining hundreds of these calculations, the network can detect complex, non-linear patterns that a human might miss.

### What is Reinforcement Learning (RL)?
**Reinforcement Learning** is different from the Supervised Learning used in our DDoS detector.
-   **Concept**: An "Agent" learns by interacting with an "Environment" to maximize a "Reward".
-   **Analogy**: Training a dog. You don't tell the dog exactly how to move its muscles (Supervised). Instead, you give it a treat (Reward) when it sits, and nothing when it doesn't. The dog learns to repeat the action that gets the treat.
-   **Components**:
    1.  **Agent**: The learner (e.g., a bot).
    2.  **Environment**: The world it lives in (e.g., a maze, a video game, or a network).
    3.  **Action**: What the agent does (e.g., move left, block an IP).
    4.  **Reward**: Positive or negative feedback (e.g., +10 points, -1 life).

#### RL vs. Our DDoS Model
| Feature | Our Current DDoS Model (Supervised) | Reinforcement Learning |
| :--- | :--- | :--- |
| **Learning Style** | **"Learn by Example"** (Teacher shows right/wrong) | **"Learn by Trial & Error"** (Experience outcome) |
| **Input** | Labeled Dataset (Historic Data) | Real-time Environment Feedback |
| **Goal** | Minimize Prediction Error | Maximize Total Reward |
| **Usage** | Great for Classification (Is this an attack?) | Great for Strategy (How should I route traffic?) |

*Note: While this project currently uses Supervised Learning for detection, RL could theoretically be used for **response** adaptation (e.g., learning the best way to mitigate an attack without blocking legitimate users).*

## 9. Standard ML Metrics Explained

When evaluating how good our model is, we use the following standard metrics. These help us understand if the model is safe to trust.

### Confusion Matrix Concepts
-   **True Positive (TP)**: We predicted **Attack**, and it actually **was** an attack. (Good!)
-   **True Negative (TN)**: We predicted **Normal**, and it actually **was** normal. (Good!)
-   **False Positive (FP)**: We predicted **Attack**, but it was **Normal**. (Bad - "False Alarm"). This causes legitimate users to get blocked.
-   **False Negative (FN)**: We predicted **Normal**, but it was an **Attack**. (Bad - "Missed Detection"). The attack succeeds.

### Key Metrics
1.  **Accuracy**:
    -   *Formula*: `(TP + TN) / Total Packets`
    -   *Meaning*: How often are we right overall?
    -   *In our Dashboard*: Displayed as "Detection Accuracy". High accuracy is good, but can be misleading if attacks are rare (a model that says "Normal" 100% of the time might still be 99% accurate if attacks are 1% of traffic).

2.  **Precision**:
    -   *Formula*: `TP / (TP + FP)`
    -   *Meaning*: When we claim it's an attack, how confident should you be?
    -   *Context*: High precision means **fewer false alarms**. In a security system, this is critical so we don't annoy users.

3.  **Recall (Sensitivity)**:
    -   *Formula*: `TP / (TP + FN)`
    -   *Meaning*: Did we catch all the attacks?
    -   *Context*: High recall means we **caught almost every attack**. If this is low, we are letting attacks slip through.

4.  **F1-Score**:
    -   *Formula*: `2 * (Precision * Recall) / (Precision + Recall)`
    -   *Meaning*: The harmonic balance between Precision and Recall. It gives a single score that punishes extreme values (e.g., effectively 0 if Recall is 0).

### Project Implementation
In `MLSecurityEngine`, we calculate these real-time:
-   **Detection Rate**: Essentially our "Positive Prediction Rate" for the recent window.
-   **False Positive Rate**: We track this if we have ground truth (often simulated in tests).
-   **Model Confidence**: The raw probability score from the neural network (0.0 to 1.0).

## 10. Step-by-Step: How to Train a Model

If you were to rebuild or train this model from scratch, here is the standard lifecycle you would follow:

### Step 1: Data Collection
-   **Goal**: Gather raw examples of what you want to learn.
-   **Action**: Capture network traffic (PCAP files). You need "Normal" traffic (browsing, email) and "Attack" traffic (DDoS tools).
-   **Result**: Gigabytes of raw log data.

### Step 2: Data Preprocessing
-   **Goal**: Turn raw data into "clean numbers" the computer can understand.
-   **Action**:
    1.  **Cleaning**: Remove broken packets or errors.
    2.  **Labeling**: Mark each packet as `0` (Normal) or `1` (Attack). This is the "Teacher's Answer Key".
    3.  **Normalization**: Scale all numbers to be between 0 and 1 (so big numbers like IP addresses don't overpower small numbers like flags).
    4.  **Feature Extraction**: Calculate the 77 features described in Section 4.

### Step 3: Train/Test Split
-   **Goal**: Ensure the model can handle *new* data, not just memorize old data.
-   **Action**: Split your dataset:
    -   **80% Training Set**: Used to teach the model.
    -   **20% Testing Set**: Hidden from the model until the end to check if it actually learned.

### Step 4: Training (The Learning Phase)
-   **Goal**: Find the mathematical patterns.
-   **Action**: Feed the 80% Training Set into the Neural Network (Section 2).
    -   **Forward Pass**: The model guesses "Normal" or "Attack".
    -   **Loss Function**: We measure how wrong the guess was.
    -   **Backpropagation**: We tweak the internal "weights" (connections) to reduce the error.
    -   **Epochs**: We repeat this process multiple times (e.g., 50 times) until the error stops going down.

### Step 5: Evaluation
-   **Goal**: Prove the model works.
-   **Action**: Run the 20% Testing Set through the model. Since the model *never* saw these packets during training, this behaves like a real-world test.
-   **Metrics**: Calculate the Accuracy, Precision, Recall, and F1 (Section 9) to verify performance. If it's good (>95%), you deploy it!
