package com.xeren.showroom.controller;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.*;

/**
 * Enterprise Spring Boot REST Controller for Xeren Progressive Car Showroom.
 */
@RestController
@RequestMapping("/api/v1/showroom")
@CrossOrigin(origins = "*")
public class CarShowroomController {

    private final List<Map<String, Object>> inventory = new ArrayList<>();

    public CarShowroomController() {
        inventory.add(Map.of(
            "id", 1,
            "modelName", "Xeren Apex Cyber-GT",
            "horsepower", 1450,
            "zeroToSixty", "1.89s",
            "rangeKm", 850,
            "priceUSD", 145000.00
        ));
        inventory.add(Map.of(
            "id", 2,
            "modelName", "Xeren Phantom Hyper-SUV",
            "horsepower", 1200,
            "zeroToSixty", "2.40s",
            "rangeKm", 780,
            "priceUSD", 120000.00
        ));
        inventory.add(Map.of(
            "id", 3,
            "modelName", "Xeren Vision Speedster",
            "horsepower", 1800,
            "zeroToSixty", "1.65s",
            "rangeKm", 920,
            "priceUSD", 220000.00
        ));
    }

    @GetMapping("/cars")
    public ResponseEntity<List<Map<String, Object>>> getCarInventory() {
        return ResponseEntity.ok(this.inventory);
    }

    @PostMapping("/book")
    public ResponseEntity<Map<String, Object>> reserveTestDrive(@RequestBody Map<String, String> payload) {
        String name = payload.getOrDefault("name", "Guest Driver");
        String model = payload.getOrDefault("carModel", "Xeren Apex Cyber-GT");
        String confirmationCode = "XR-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();

        Map<String, Object> response = new HashMap<>();
        response.put("status", "CONFIRMED");
        response.put("confirmationCode", confirmationCode);
        response.put("message", "VIP test drive reserved for " + name + " in the " + model);

        return ResponseEntity.ok(response);
    }
}
