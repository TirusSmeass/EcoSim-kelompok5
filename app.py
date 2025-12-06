from flask import Flask, render_template, jsonify, request
import json
import os
import random
from datetime import datetime

app = Flask(__name__)

# Game state
game_state = {
    "points": 10000,
    "score": 0,
    "biodiversity": 0,
    "plants": [],
    "animals": [],
    "food_chains": [],
    "achievements": [],
    "activities": ["[00:00] Welcome to EcoSim!"],
    "total_plants": 0,
    "total_animals": 0,
    "tutorial_completed": False
}

# Plant data with animal attractions
PLANT_DATA = {
    "oak": {
        "cost": 200,
        "attractions": {
            "seed": [],
            "sprout": [],
            "young": ["bird"],
            "mature": ["bird", "squirrel"],
            "fully_grown": ["bird", "squirrel", "owl"]
        }
    },
    "rose": {
        "cost": 150,
        "attractions": {
            "seed": [],
            "sprout": [],
            "young": [],
            "mature": ["bee", "butterfly"],
            "fully_grown": ["bee", "butterfly", "ladybug"]
        }
    },
    "sunflower": {
        "cost": 100,
        "attractions": {
            "seed": [],
            "sprout": [],
            "young": [],
            "mature": ["bee"],
            "fully_grown": ["bee", "bird"]
        }
    },
    "berry": {
        "cost": 250,
        "attractions": {
            "seed": [],
            "sprout": [],
            "young": [],
            "mature": ["bird"],
            "fully_grown": ["bird", "deer", "rabbit"]
        }
    }
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/game_state', methods=['GET'])
def get_game_state():
    return jsonify(game_state)

@app.route('/api/tutorial_status', methods=['GET'])
def get_tutorial_status():
    return jsonify({"completed": game_state["tutorial_completed"]})

@app.route('/api/tutorial_complete', methods=['POST'])
def complete_tutorial():
    game_state["tutorial_completed"] = True
    return jsonify({"status": "success", "message": "Tutorial completed"})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    fully_grown = len([p for p in game_state["plants"] if p.get("stage") == "fully_grown"])
    return jsonify({
        "total_plants": len(game_state["plants"]),
        "total_animals": len(game_state["animals"]),
        "biodiversity": game_state["biodiversity"],
        "score": game_state["score"],
        "food_chains": len(game_state["food_chains"]),
        "fully_grown": fully_grown
    })

@app.route('/api/plant', methods=['POST'])
def add_plant():
    try:
        data = request.json
        plant_type = data.get('type')
        x = data.get('x')
        y = data.get('y')
        
        # Validation
        if plant_type not in PLANT_DATA:
            return jsonify({"status": "error", "message": "Invalid plant type"})
        
        cost = PLANT_DATA[plant_type]["cost"]
        
        # Check if occupied
        for plant in game_state["plants"]:
            if plant["x"] == x and plant["y"] == y:
                return jsonify({"status": "error", "message": "Position already occupied"})
        
        # Check points
        if game_state["points"] < cost:
            return jsonify({"status": "error", "message": "Not enough points"})
        
        # Add plant
        new_plant = {
            "type": plant_type,
            "x": x,
            "y": y,
            "growth": 0,
            "stage": "seed",
            "health": 100,
            "planted_at": datetime.now().isoformat()
        }
        
        game_state["plants"].append(new_plant)
        game_state["points"] -= cost
        game_state["total_plants"] = len(game_state["plants"])
        
        # Get attracted animals for this new plant
        attracted_animals = PLANT_DATA[plant_type]["attractions"]["seed"]
        new_animals = []
        
        for animal in attracted_animals:
            if animal not in game_state["animals"]:
                game_state["animals"].append(animal)
                new_animals.append(animal)
        
        game_state["total_animals"] = len(game_state["animals"])
        
        # Update ecosystem
        update_ecosystem()
        
        # Add activity
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        game_state["activities"].insert(0, f"{timestamp} Planted {plant_type} at ({x}, {y})")
        if len(game_state["activities"]) > 10:
            game_state["activities"] = game_state["activities"][:10]
        
        # Check achievements
        check_achievements()
        
        return jsonify({
            "status": "success",
            "message": f"Planted {plant_type}!",
            "game_state": game_state,
            "new_animals": new_animals,
            "plant_position": {"x": x, "y": y}
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/grow', methods=['POST'])
def grow_plants():
    try:
        old_animals = set(game_state["animals"])
        new_animals_list = []
        
        # Grow each plant
        for plant in game_state["plants"]:
            if plant["growth"] < 100:
                plant["growth"] = min(100, plant["growth"] + 15)
                
                # Update stage
                if plant["growth"] < 20:
                    plant["stage"] = "seed"
                elif plant["growth"] < 40:
                    plant["stage"] = "sprout"
                elif plant["growth"] < 60:
                    plant["stage"] = "young"
                elif plant["growth"] < 80:
                    plant["stage"] = "mature"
                else:
                    plant["stage"] = "fully_grown"
                
                # Add points for growth
                game_state["points"] += 30
        
        # Update ecosystem
        update_ecosystem()
        
        # Check for new animals
        new_animals = [a for a in game_state["animals"] if a not in old_animals]
        
        # Get positions of mature plants for animal animations
        mature_plants = []
        for plant in game_state["plants"]:
            if plant["stage"] in ["mature", "fully_grown"]:
                mature_plants.append({
                    "x": plant["x"],
                    "y": plant["y"],
                    "type": plant["type"]
                })
        
        # Add activity
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        game_state["activities"].insert(0, f"{timestamp} Grew all plants")
        if len(game_state["activities"]) > 10:
            game_state["activities"] = game_state["activities"][:10]
        
        return jsonify({
            "status": "success",
            "message": "Plants grew successfully!",
            "plants": game_state["plants"],
            "new_animals": new_animals,
            "mature_plants": mature_plants,
            "game_state": game_state
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/reset', methods=['POST'])
def reset_game():
    global game_state
    game_state = {
        "points": 10000,
        "score": 0,
        "biodiversity": 0,
        "plants": [],
        "animals": [],
        "food_chains": [],
        "achievements": [],
        "activities": ["[00:00] Game was reset"],
        "total_plants": 0,
        "total_animals": 0,
        "tutorial_completed": False
    }
    return jsonify({"status": "success", "message": "Game reset successfully"})

def update_ecosystem():
    # Update animals based on plant stages
    all_attracted_animals = set()
    
    for plant in game_state["plants"]:
        attractions = PLANT_DATA[plant["type"]]["attractions"][plant["stage"]]
        all_attracted_animals.update(attractions)
    
    game_state["animals"] = list(all_attracted_animals)
    game_state["total_animals"] = len(game_state["animals"])
    
    # Update biodiversity
    species = set()
    for plant in game_state["plants"]:
        species.add(plant["type"])
    for animal in game_state["animals"]:
        species.add(animal)
    game_state["biodiversity"] = min(100, (len(species) / 10) * 100)
    
    # Update food chains
    update_food_chains()
    
    # Update score
    update_score()

def update_food_chains():
    game_state["food_chains"] = []
    mature_plants = [p for p in game_state["plants"] if p["stage"] in ["mature", "fully_grown"]]
    
    # Simple food chains
    if any(p["type"] == "berry" for p in mature_plants) and "bird" in game_state["animals"]:
        game_state["food_chains"].append("🫐 Berry Bush → 🐦 Bird")
    if any(p["type"] == "rose" for p in mature_plants) and "butterfly" in game_state["animals"]:
        game_state["food_chains"].append("🌹 Rose → 🦋 Butterfly")
    if any(p["type"] == "oak" for p in mature_plants) and "squirrel" in game_state["animals"]:
        game_state["food_chains"].append("🌳 Oak Tree → 🐿️ Squirrel")
    if any(p["type"] == "sunflower" for p in mature_plants) and "bee" in game_state["animals"]:
        game_state["food_chains"].append("🌻 Sunflower → 🐝 Bee")

def update_score():
    plant_score = len(game_state["plants"]) * 100
    animal_score = len(game_state["animals"]) * 200
    biodiversity_bonus = game_state["biodiversity"] * 20
    food_chain_bonus = len(game_state["food_chains"]) * 150
    fully_grown_bonus = len([p for p in game_state["plants"] if p["stage"] == "fully_grown"]) * 250
    
    game_state["score"] = int(plant_score + animal_score + biodiversity_bonus + food_chain_bonus + fully_grown_bonus)

def check_achievements():
    achievements = []
    
    if len(game_state["plants"]) >= 1 and "First Planter" not in game_state["achievements"]:
        game_state["achievements"].append("First Planter")
        achievements.append("First Planter")
    
    if "butterfly" in game_state["animals"] and "Butterfly Friend" not in game_state["achievements"]:
        game_state["achievements"].append("Butterfly Friend")
        achievements.append("Butterfly Friend")
    
    if game_state["biodiversity"] >= 50 and "Ecosystem Builder" not in game_state["achievements"]:
        game_state["achievements"].append("Ecosystem Builder")
        achievements.append("Ecosystem Builder")
    
    return achievements

if __name__ == '__main__':
    # Create templates folder
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("=" * 60)
    print("🌿 EcoSim Server v2.0 - WITH ANIMATIONS!")
    print("🌐 Server: http://localhost:5000")
    print("🎬 Features: Tutorial Animations + Animal Animations")
    print("=" * 60)
    
    app.run(debug=True, port=5000)