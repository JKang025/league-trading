# league-trading
Aim to have a ML model that is able to predict win% of a game given the draft of a pro play day. Use this to trade programatically on Kalshi and Polymarket.

## Motivation
I've been dabbling in LOL based projects for as long as I have been coding (just look at my github). This recent burst of inspiration was to due discovering event contract sites like Polymarket and Kalshi that not only are completely legal, but have very developer friendly APIs to trade on. This is contrast to betting sites, which I have also dabbled in before, where they heavily discourage interacting with them programatically

## Goals
1. Robust system of querying, extracting, and storing match data 
2. Develop a model that will give me a genuine edge in these event markets
3. Periodic training and retraining pipeline
4. Real-time feature extraction job
5. Execution system that allows programatic trading, using the model output as edge
