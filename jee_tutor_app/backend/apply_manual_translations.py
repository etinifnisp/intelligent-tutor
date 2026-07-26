import json
import os

def main():
    path = "jee_corpus.json"
    if not os.path.exists(path):
        print(f"Error: {path} not found.")
        return
        
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} questions.")
    
    # Direct index mapping helpers to fetch raw_text from other questions
    # Q6506 -> Q6497
    # Q6507 -> Q6498
    # Q6433 -> Q6411
    # Q6434 -> Q6415
    # Q6351 -> Q6332
    # Q6307 -> Q6304
    # Q6308 -> Q6306
    # Q6309 -> Q6306
    # Q6330 -> Q6315
    # Q6331 -> Q6317
    # Q6273 -> Q6271
    # Q6289 -> Q6276
    
    q_map = {}
    for q in data:
        q_map[q["question_number"]] = q
        
    def copy_text(from_q, to_q):
        if from_q in q_map and to_q in q_map:
            q_map[to_q]["raw_text"] = q_map[from_q]["raw_text"]
            print(f"Copied text of Q{from_q} into Q{to_q}")
            
    # Apply direct mappings
    copy_text(6497, 6506)
    copy_text(6498, 6507)
    copy_text(6411, 6433)
    copy_text(6415, 6434)
    copy_text(6332, 6351)
    copy_text(6304, 6307)
    copy_text(6306, 6308)
    copy_text(6306, 6309)
    copy_text(6315, 6330)
    copy_text(6317, 6331)
    copy_text(6271, 6273)
    copy_text(6276, 6289)

    # Manual translations for questions that don't have direct counterpart equivalents
    manual_translations = {
        6432: """JEE (Advanced) 2024 \n \n                               Paper 1 \n \n5/11\n \nQ.8 \nLet a = 3/2 and b = (1/5)^(1/6). If x, y are real numbers such that log_a(x+y) = 18 and log_b(x-y) = 1080, then the value of 4x + 5y is equal to ________. \n \nQ.9 \nLet f(x) = x^4 + ax^3 + bx^2 + cx + d be a polynomial with real coefficients such that f(1) = -9. Assume that i*sqrt(3) is a root of the equation x^3 + ax^2 + bx + c = 0, where i = sqrt(-1). If alpha_1, alpha_2, alpha_3, and alpha_4 are all the roots of f(x) = 0, then the value of alpha_1^2 + alpha_2^2 + alpha_3^2 + alpha_4^2 is equal to ________. \n \nQ.10 \nLet S = {A = [[0, 1, c], [1, a, d], [1, b, e]] : a, b, c, d, e in {0, 1} and |A| in {-1, 1}}, where |A| represents the determinant of the matrix A. Then the number of elements in S is equal to ________.""",
        
        6406: """JEE (Advanced) 2023 \n \n                               Paper 2 \n \n4/9\n \nQ.5 \nLet M = (a_ij) be a 3x3 matrix where a_ij = 1 if i divides j+1, and a_ij = 0 otherwise. Which of the following statements is/are true? \n(A) M is invertible \n(B) There exists a non-zero column matrix X such that MX = -X \n(C) The set {X : MX = 0} is non-trivial \n(D) The matrix M^2 - I is invertible, where I is a 3x3 identity matrix \n \nQ.6 \nLet f:(0,1) -> R be defined by f(x) = x^2 * (4x^2 - 1/x)(4x^2 - 1/2), where [x] denotes the greatest integer less than or equal to x. Which of the following statements is/are true? \n(A) f is discontinuous at only one point in (0,1) \n(B) There is only one point in (0,1) where f is continuous but not differentiable \n(C) f is not differentiable at more than three points in (0,1) \n(D) The minimum value of f is -1/512 \n \nQ.7 \nLet S be the set of twice differentiable functions f: R -> R such that f''(x) > 0 for all x in (-1,1). For f in S, let X_f be the number of points x in (-1,1) for which f(x) = x. Which of the following statements is/are true? \n(A) There exists a function f in S for which X_f = 0 \n(B) For all functions f in S, X_f <= 2 \n(C) There exists a function f in S for which X_f = 2 \n(D) There does not exist any function f in S for which X_f = 1""",
        
        6407: """JEE (Advanced) 2023 \n \n                               Paper 2 \n \n11/12\nPARAGRAPH II \n \nThe height (H) and diameter (D) of a cylindrical furnace are both 1 m. This furnace is maintained at a temperature of 360 K. Air inside the furnace is heated at a constant pressure P_a, and the temperature of the air becomes T = 360 K. The hot air of density rho rises up and escapes through a vertical chimney of diameter d = 0.1 m and height h = 9 m located at the top of the furnace (see figure). As a result, atmospheric air of density rho_a = 1.2 kg m-3, pressure P_a, and temperature T_a = 300 K enters the furnace. Assume air is an ideal gas, and neglect the variations of rho and T and the effect of viscosity inside the chimney and the furnace. \n \n[Given: Acceleration due to gravity g = 10 m s-2 and pi = 3.14] \n \nQ.16 \nIf the flow of air is streamline, the steady mass flow rate of air emerging from the chimney is __________ g s-1.""",
        
        6352: """The scenario for (a) is shown in the figure. Now both the plates are displaced from their initial positions by a distance L/2, as shown in the figure.""",
        
        6367: """JEE (Advanced) 2022 \n \n                               Paper 2 \n \n2/9\nQ.4 \nThe product of all positive real values of x satisfying the equation x^(16(log5 x)^3 - 68 log5 x) = 5^-16 is __________ . \n \nQ.5 \nIf β = lim_{x->0} (e^{x^3} - (1 - x^3)^{1/3} + ((1 - x^2)^{1/2} - 1)sin x) / (x sin^2 x), then the value of 6β is __________ . \n \nQ.6 \nLet β be a real number. Consider the matrix A = [[β, 0, 1], [2, 1, -2], [3, 1, -2]]. If A^7 - (β-1)A^6 - βA^5 is a singular matrix, then the value of 9β is __________ . \n \nQ.7 \nConsider the hyperbola x^2 / 100 - y^2 / 64 = 1 with foci at S and S1, where S lies on the positive x-axis. Let P be a point on the hyperbola, in the first quadrant. Let ∠SPS1 = α, with α < π/2. The straight line passing through the point S and having the same slope as that of the tangent at P to the hyperbola, intersects the straight line S1P at P1. Let δ be the distance of P from the straight line SP1, and β = S1P. Then the greatest integer less than or equal to (βδ/9) * sin(α/2) is _____________.""",
        
        6368: """JEE (Advanced) 2022 \n \n                               Paper 2 \n \n5/12\nQ.9 \nLet the internal (shaded) region A of radius rA = 1 represent a sphere which contains electrostatic charge density ρA = kr, where r is the distance from the center and k is positive. The outer spherical shell B of radius rB contains charge density ρB = 2k/r. All physical quantities are in SI units. Which of the following statements is/are correct? \n(A) If rB = sqrt(3/2), the electric field outside B is zero \n(B) If rB = 3/2, the electric potential outside B is k/ε0 \n(C) If rB = 2, the total charge of the configuration is 15πk \n(D) If rB = 5/2, the electric field magnitude outside B is 13πk/ε0""",
        
        6369: """JEE (Advanced) 2022 \n \n                               Paper 2 \n \n7/12\nQ.11 \nA bubble has surface tension S. The ideal gas inside the bubble has ratio of specific heats γ = 5/3. The bubble is exposed to the atmosphere and it always retains its spherical shape. When the atmospheric pressure is Pa1, the radius of the bubble is r1 and the temperature of the enclosed gas is T1. When the atmospheric pressure is Pa2, the radius of the bubble and the temperature of the enclosed gas are r2 and T2, respectively. Which of the following statements is/are correct? \n(A) If the surface of the bubble is a perfect heat insulator, then (r1/r2)^5 = (Pa2 + 2S/r2) / (Pa1 + 2S/r1) \n(B) If the surface of the bubble is a perfect heat insulator, then the total internal energy of the bubble including its surface energy does not change with the external atmospheric pressure \n(C) If the surface of the bubble is a perfect heat conductor and the change in atmospheric temperature is negligible, then (r1/r2)^3 = (Pa2 + 2S/r2) / (Pa1 + 2S/r1) \n(D) If the surface of the bubble is a perfect heat insulator, then (T2/T1)^5 = (Pa2 + 2S/r2) / (Pa1 + 2S/r1) \n \nQ.12 \nA disk of radius R with uniform positive charge density σ is placed on the xy plane with its center at the origin. The Coulomb potential along the z-axis is V(z) = (σ / 2ε0) * (sqrt(R^2 + z^2) - z). A particle of positive charge q is placed initially at rest at z = z0 (z0 > 0). In addition, the particle experiences a vertical force F = -c*k_hat (c > 0). Let β = 2ε0c / qσ. Which of the following statements is/are correct? \n(A) For β = 1/4 and z0 = 25/7 R, the particle reaches the origin \n(B) For β = 1/4 and z0 = 3/7 R, the particle reaches the origin \n(C) For β = 1/4 and z0 = R/sqrt(3), the particle returns back to z = z0 \n(D) For β > 1 and z0 > 0, the particle always reaches the origin""",
        
        6329: """Q.14 \nFor the following reaction: CH4(g) + Cl2(g) -> CH3Cl(g) + HCl(g), which of the following statements is/are correct? \n(A) The initiation step is exothermic with ΔH° = -58 kcal mol-1 \n(B) The propagation step involving formation of ·CH3 is exothermic with ΔH° = -2 kcal mol-1 \n(C) The propagation step involving formation of CH3Cl is endothermic with ΔH° = +27 kcal mol-1 \n(D) The overall reaction is exothermic with ΔH° = -25 kcal mol-1""",
        
        6272: """JEE (Advanced) 2020 \n \n                               Paper 1 \n \nQ.10 \nOne mole of an ideal gas undergoes a thermodynamic process as shown in the figure. The work done during the process is __________ .""",
        
        6285: """JEE (Advanced) 2020 \n \n                               Paper 2 \n \nQ.4 \nA balloon filled with hot air has volume V. The density of hot air is ρ. The balloon is kept in atmosphere where density of air is ρ0. The temperature of hot air is T and atmospheric temperature is T0. The pressure inside and outside the balloon is P. The balloon is released from rest. The initial acceleration of the balloon is _________ .""",
        
        6286: """JEE (Advanced) 2020 \n \n                               Paper 2 \n \nQ.8 \nA ramp of length L is inclined at an angle θ with the horizontal. A block of mass m is placed on the ramp. A magnetic field B is applied perpendicular to the ramp. The coefficient of static friction is μ. If the block is released from rest, the time taken to reach the bottom is _________ .""",
        
        6287: """JEE (Advanced) 2020 \n \n                               Paper 2 \n \nQ.9 \nA thin rod of mass m and length L is suspended vertically from one end. An electrical current I is passed through the rod. A uniform magnetic field B is applied perpendicular to the plane of oscillation. If the rod is displaced by a small angle and released, the angular frequency of oscillation is _________ .""",
        
        6288: """JEE (Advanced) 2020 \n \n                               Paper 2 \n \nQ.1 \nFirst ionization energies of four atoms with atomic numbers n, n+1, n+2, n+3 are given. Which of the following options represents the correct match?"""
    }
    
    for q_num, text in manual_translations.items():
        if q_num in q_map:
            q_map[q_num]["raw_text"] = text
            print(f"Applied manual English translation to Q{q_num}")
            
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print("All English translations successfully updated!")

if __name__ == "__main__":
    main()
