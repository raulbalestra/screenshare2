#!/bin/bash

# Step 1: Deploy Flask app
echo "Deploying Flask App..."
python3 app.py > logs.txt

# Step 2: Analyze logs using OpenAI API
echo "Analyzing logs..."
python3 analyze_logs.py logs.txt
