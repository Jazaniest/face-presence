import cv2
import face_recognition
import json
import os
import numpy as np
import time
from sklearn.metrics.pairwise import cosine_similarity

DB_FILE = "face_embeddings.json"

def load_database():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_database(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

def variance_of_laplacian(image):
    """Menghitung fokus gambar menggunakan variance of Laplacian"""
    return cv2.Laplacian(image, cv2.CV_64F).var()

def calculate_brightness(image):
    """Menghitung tingkat kecerahan gambar"""
    return np.mean(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))

def calculate_contrast(image):
    """Menghitung kontras gambar menggunakan standard deviation"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return np.std(gray)

def is_face_centered(face_location, frame_shape):
    """Mengecek apakah wajah berada di tengah frame"""
    top, right, bottom, left = face_location
    frame_h, frame_w = frame_shape[:2]
    
    face_center_x = (left + right) // 2
    face_center_y = (top + bottom) // 2
    frame_center_x = frame_w // 2
    frame_center_y = frame_h // 2
    
    # Toleransi 25% dari ukuran frame
    tolerance_x = frame_w * 0.25
    tolerance_y = frame_h * 0.25
    
    return (abs(face_center_x - frame_center_x) < tolerance_x and 
            abs(face_center_y - frame_center_y) < tolerance_y)

def calculate_face_angle_score(landmarks):
    """Menghitung skor berdasarkan posisi wajah (frontal lebih baik)"""
    if not landmarks:
        return 0
    
    # Ambil landmark mata dan hidung
    left_eye = np.array(landmarks[0]['left_eye'])
    right_eye = np.array(landmarks[0]['right_eye'])
    nose_tip = np.array(landmarks[0]['nose_tip'])
    
    # Hitung simetri mata
    eye_center = (left_eye.mean(axis=0) + right_eye.mean(axis=0)) / 2
    nose_center = nose_tip.mean(axis=0)
    
    # Skor berdasarkan seberapa tengah hidung relatif terhadap mata
    horizontal_symmetry = abs(nose_center[0] - eye_center[0])
    
    # Semakin kecil asymmetry, semakin bagus (frontal)
    return max(0, 100 - horizontal_symmetry)

def quality_score(frame, face_location, face_landmarks):
    """Menghitung skor kualitas gambar secara komprehensif"""
    top, right, bottom, left = face_location
    
    # ROI wajah
    face_roi = frame[top:bottom, left:right]
    face_roi_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    
    # Berbagai metrik kualitas
    blur_score = variance_of_laplacian(face_roi_gray)
    brightness = calculate_brightness(face_roi)
    contrast = calculate_contrast(face_roi)
    face_size = (bottom - top) * (right - left)
    is_centered = is_face_centered(face_location, frame.shape)
    angle_score = calculate_face_angle_score(face_landmarks)
    
    # Normalisasi dan bobot
    scores = {
        'blur': min(blur_score / 100.0, 1.0) * 30,
        'brightness': (1 - abs(brightness - 128) / 128.0) * 20,
        'contrast': min(contrast / 50.0, 1.0) * 15,
        'size': min(face_size / 40000.0, 1.0) * 20,
        'centered': 10 if is_centered else 0,
        'angle': angle_score / 100.0 * 5
    }
    
    total_score = sum(scores.values())
    return total_score, scores

def remove_outliers(embeddings_list, threshold=0.15):
    """Menghapus embedding yang terlalu berbeda (outlier)"""
    if len(embeddings_list) < 3:
        return embeddings_list
    
    # Hitung similarity matrix
    similarities = []
    for i, emb1 in enumerate(embeddings_list):
        row_sim = []
        for j, emb2 in enumerate(embeddings_list):
            if i != j:
                sim = cosine_similarity([emb1], [emb2])[0][0]
                row_sim.append(sim)
        if row_sim:
            similarities.append(np.mean(row_sim))
        else:
            similarities.append(0)
    
    # Buang embedding dengan similarity rendah
    good_embeddings = []
    mean_similarity = np.mean(similarities)
    
    for i, sim in enumerate(similarities):
        if sim >= mean_similarity - threshold:
            good_embeddings.append(embeddings_list[i])
    
    return good_embeddings if good_embeddings else embeddings_list[:1]

def main():
    database = load_database()
    print("Database wajah yang ada:", list(database.keys()))

    user_name = input("Masukkan Nama Karyawan untuk Registrasi: ")
    if user_name in database:
        print(f"Error: Nama '{user_name}' sudah terdaftar.")
        return
    if not user_name:
        print("Error: Nama tidak boleh kosong.")
        return

    video_capture = cv2.VideoCapture(0)
    
    # Set resolusi kamera untuk kualitas lebih baik
    video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # Parameter yang ditingkatkan
    embeddings_data = []  
    max_samples = 15 
    min_samples = 8 
    min_quality_score = 70
    
    instructions = [
        "Lihat LURUS ke kamera", 
        "Lihat sedikit ke KIRI", 
        "Lihat sedikit ke KANAN",
        "Lihat sedikit ke ATAS",
        "Lihat sedikit ke BAWAH"
    ]
    current_instruction_idx = 0
    instruction_display_time = 3
    last_instruction_time = time.time()
    samples_per_pose = 3
    current_pose_samples = 0
    
    print(f"\n🎯 Target: Kumpulkan {min_samples}-{max_samples} sampel berkualitas tinggi")
    print("📋 Instruksi akan berganti otomatis. Tekan 'q' untuk berhenti.\n")
    
    while len(embeddings_data) < max_samples:
        ret, frame = video_capture.read()
        if not ret:
            print("Gagal mengambil frame dari kamera.")
            break

        current_instruction = instructions[current_instruction_idx]
        
        # Beri jeda antar instruksi
        if time.time() - last_instruction_time < instruction_display_time:
            (h, w) = frame.shape[:2]
            cv2.putText(frame, current_instruction, (w // 6, h // 2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)
            cv2.putText(frame, current_instruction, (w // 6, h // 2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            cv2.imshow('Video Registrasi Wajah', frame)
            cv2.waitKey(1)
            continue
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Deteksi wajah dan landmark
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        face_landmarks = face_recognition.face_landmarks(rgb_frame, face_locations)

        if len(face_locations) == 1:
            top, right, bottom, left = face_locations[0]
            
            # Hitung kualitas
            quality, quality_breakdown = quality_score(frame, face_locations[0], face_landmarks)
            
            # Warna kotak berdasarkan kualitas
            if quality >= min_quality_score:
                box_color = (0, 255, 0) 
                status_text = f"EXCELLENT! Skor: {quality:.1f}"
                status_color = (0, 255, 0)
            elif quality >= min_quality_score * 0.8:
                box_color = (0, 255, 255) 
                status_text = f"Baik. Skor: {quality:.1f}"
                status_color = (0, 255, 255)
            else:
                box_color = (0, 0, 255)
                status_text = f"Rendah. Skor: {quality:.1f}"
                status_color = (0, 0, 255)
            
            cv2.rectangle(frame, (left, top), (right, bottom), box_color, 2)
            cv2.putText(frame, status_text, (left, top - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
            
            # Tampilkan detail kualitas
            y_offset = 30
            for metric, score in quality_breakdown.items():
                detail_text = f"{metric}: {score:.1f}"
                cv2.putText(frame, detail_text, (10, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                y_offset += 20
            
            # Ambil sampel jika kualitas bagus
            if quality >= min_quality_score:
                face_encodings = face_recognition.face_encodings(rgb_frame, [face_locations[0]])
                if face_encodings:
                    embedding = face_encodings[0]
                    embeddings_data.append({
                        'embedding': embedding,
                        'quality': quality,
                        'pose': current_instruction
                    })
                    
                    current_pose_samples += 1
                    print(f"✅ Sampel {len(embeddings_data)}/{max_samples} | "
                          f"Pose: {current_instruction} | Skor: {quality:.1f}")
                    
                    # Feedback visual
                    cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 255), 4)
                    cv2.imshow('Video Registrasi Wajah', frame)
                    cv2.waitKey(300)
                    
                    # Ganti pose setelah cukup sampel atau otomatis setelah waktu tertentu
                    if current_pose_samples >= samples_per_pose:
                        current_instruction_idx = (current_instruction_idx + 1) % len(instructions)
                        current_pose_samples = 0
                        last_instruction_time = time.time()
        
        # Info di layar
        progress_text = f"Progress: {len(embeddings_data)}/{max_samples} | {current_instruction}"
        cv2.putText(frame, progress_text, (10, frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow('Video Registrasi Wajah', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):  
            # Space untuk ganti pose manual
            current_instruction_idx = (current_instruction_idx + 1) % len(instructions)
            current_pose_samples = 0
            last_instruction_time = time.time()

    video_capture.release()
    cv2.destroyAllWindows()
    
    # Proses hasil
    if len(embeddings_data) >= min_samples:
        print(f"\n📊 Menganalisis {len(embeddings_data)} sampel...")
        
        # Urutkan berdasarkan kualitas
        embeddings_data.sort(key=lambda x: x['quality'], reverse=True)
        
        # Ambil embedding terbaik
        best_embeddings = [data['embedding'] for data in embeddings_data[:12]]
        
        # Hapus outlier
        filtered_embeddings = remove_outliers(best_embeddings)
        print(f"📈 Setelah filter outlier: {len(filtered_embeddings)} sampel")
        
        if filtered_embeddings:
            # Hitung embedding final dengan weighted average
            weights = []
            for i, emb in enumerate(filtered_embeddings):
                # Cari kualitas asli dari embedding ini
                quality = next((data['quality'] for data in embeddings_data 
                              if np.array_equal(data['embedding'], emb)), 70)
                weights.append(quality)
            
            weights = np.array(weights)
            weights = weights / np.sum(weights)  # Normalisasi
            
            # Weighted average
            final_embedding = np.average(filtered_embeddings, axis=0, weights=weights)
            
            # Simpan ke database
            database[user_name] = final_embedding.tolist()
            save_database(database)
            
            avg_quality = np.mean([data['quality'] for data in embeddings_data[:len(filtered_embeddings)]])
            print(f"\n✅ REGISTRASI BERHASIL!")
            print(f"👤 Nama: {user_name}")
            print(f"📊 Sampel digunakan: {len(filtered_embeddings)}")
            print(f"🏆 Rata-rata kualitas: {avg_quality:.1f}")
            print(f"💾 Data disimpan ke {DB_FILE}")
        else:
            print("\n❌ Tidak ada embedding yang memenuhi standar kualitas.")
    else:
        print(f"\n❌ Registrasi dibatalkan. Hanya {len(embeddings_data)} sampel terkumpul (minimum {min_samples}).")

    print("🔚 Program selesai.")

if __name__ == "__main__":
    main()