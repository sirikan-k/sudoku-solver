import sys
import copy
import numpy as np
import streamlit as st

# ตรวจสอบ Library สำหรับอ่านรูปภาพ
try:
    import cv2
    import pytesseract
    from PIL import Image
    HAS_IMAGE_OCR = True
except ImportError:
    HAS_IMAGE_OCR = False

def parse_txt_content(content_str):
    """แปลงเนื้อหาจากไฟล์ข้อความ .txt เป็นตาราง 2 มิติขนาด 9x9"""
    lines = content_str.strip().split('\n')
    board = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        row = [int(x) for x in line.split()]
        if len(row) == 9:
            board.append(row)
    if len(board) != 9:
        raise ValueError("รูปแบบตารางไม่ตรงตามขนาด 9x9")
    return board

def parse_image_to_board(image_bytes):
    """ตัดช่องตารางจากรูปภาพและใช้อัลกอริทึม OCR อ่านตัวเลข 1-9"""
    if not HAS_IMAGE_OCR:
        raise RuntimeError("ระบบยังไม่ได้ติดตั้ง OpenCV หรือ PyTesseract")
        
    file_bytes = np.asarray(bytearray(image_bytes), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # ปรับขนาดภาพเป็น 450x450 เพื่อแบ่งช่องละ 50x50
    resized = cv2.resize(gray, (450, 450))
    
    board = []
    for r in range(9):
        row = []
        for c in range(9):
            # ตัดช่องเฉพาะส่วนกลางเพื่อหลบเส้นขอบตาราง
            cell = resized[r*50:(r+1)*50, c*50:(c+1)*50]
            cell_cropped = cell[6:44, 6:44]
            
            # แปลงภาพเป็นขาวดำ
            _, thresh = cv2.threshold(cell_cropped, 160, 255, cv2.THRESH_BINARY_INV)
            
            # ตรวจสอบว่ามีพิกเซลตัวเลขหรือไม่
            if cv2.countNonZero(thresh) < 25:
                row.append(0)
            else:
                config = '--psm 10 --oem 3 -c tessedit_char_whitelist=123456789'
                text = pytesseract.image_to_string(cell_cropped, config=config).strip()
                row.append(int(text) if text.isdigit() else 0)
        board.append(row)
    return board

def check_initial_conflicts_detailed(board):
    """ตรวจสอบความขัดแย้งของโจทย์เริ่มต้น"""
    conflicts = []
    for r in range(9):
        for c in range(9):
            num = board[r][c]
            if num != 0:
                for c2 in range(c + 1, 9):
                    if board[r][c2] == num:
                        conflicts.append(f"เลข **{num}** ซ้ำกันในแถวที่ {r+1} (ตำแหน่งหลักที่ {c+1} และ {c2+1})")
                for r2 in range(r + 1, 9):
                    if board[r2][c] == num:
                        conflicts.append(f"เลข **{num}** ซ้ำกันในหลักที่ {c+1} (ตำแหน่งแถวที่ {r+1} และ {r2+1})")
                sr, sc = 3 * (r // 3), 3 * (c // 3)
                for r2 in range(sr, sr + 3):
                    for c2 in range(sc, sc + 3):
                        if (r2 > r or (r2 == r and c2 > c)) and board[r2][c2] == num:
                            if r2 != r and c2 != c:
                                conflicts.append(
                                    f"เลข **{num}** ซ้ำกันในบล็อก 3x3 เดียวกัน "
                                    f"(ตำแหน่ง แถว {r+1} หลัก {c+1} กับ แถว {r2+1} หลัก {c2+1})"
                                )
    return conflicts

def is_valid(board, row, col, num):
    for i in range(9):
        if board[row][i] == num or board[i][col] == num:
            return False
    start_row, start_col = 3 * (row // 3), 3 * (col // 3)
    for i in range(3):
        for j in range(3):
            if board[start_row + i][start_col + j] == num:
                return False
    return True

def find_empty(board):
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return r, c
    return None

def solve_and_count(board, solutions):
    if len(solutions) >= 2:
        return

    empty = find_empty(board)
    if not empty:
        solutions.append(copy.deepcopy(board))
        return

    row, col = empty
    for num in range(1, 10):
        if is_valid(board, row, col, num):
            board[row][col] = num
            solve_and_count(board, solutions)
            board[row][col] = 0

def process_sudoku(board):
    original_board = copy.deepcopy(board)
    conflicts = check_initial_conflicts_detailed(board)
    if conflicts:
        return "INITIAL_CONFLICT", None, conflicts, original_board

    if find_empty(board) is None:
        return "COMPLETED", board, [], original_board

    solutions = []
    solve_and_count(board, solutions)

    if len(solutions) == 0:
        reasons = ["โจทย์ไม่มีข้อขัดแย้งเริ่มต้น แต่เกิดสถานการณ์ทางตัน (Deadlock) ระหว่าง Backtracking ทำให้ไม่มีตัวเลขที่ลงได้ตามกฎ"]
        return "NO_SOLUTION", None, reasons, original_board
    elif len(solutions) == 1:
        return "SUCCESS", solutions[0], [], original_board
    else:
        reasons = ["โจทย์ระบุตัวเลขเริ่มต้นน้อยเกินไป ทำให้ตารางมีรูปแบบคำตอบที่เป็นไปได้มากกว่า 1 ชุด"]
        return "MULTIPLE_SOLUTIONS", None, reasons, original_board

def render_sudoku_html(board, original_board=None):
    html = """
    <style>
        .sudoku-container { display: flex; justify-content: center; margin: 15px 0; }
        .sudoku-table { border-collapse: collapse; border: 3px solid #111111; background-color: #ffffff; }
        .sudoku-table td { width: 42px; height: 42px; text-align: center; font-size: 20px; font-weight: bold; border: 1px solid #b0b0b0; }
        .border-right-thick { border-right: 3px solid #111111 !important; }
        .border-bottom-thick { border-bottom: 3px solid #111111 !important; }
        .given-number { color: #111111; }
        .filled-number { color: #2563eb; }
        .empty-cell { color: transparent; }
    </style>
    <div class="sudoku-container"><table class="sudoku-table">
    """
    for r in range(9):
        html += "<tr>"
        for c in range(9):
            classes = []
            if (c + 1) % 3 == 0 and c < 8: classes.append("border-right-thick")
            if (r + 1) % 3 == 0 and r < 8: classes.append("border-bottom-thick")
            
            val = board[r][c]
            if val == 0:
                classes.append("empty-cell")
                display_val = "0"
            else:
                display_val = str(val)
                if original_board and original_board[r][c] == 0:
                    classes.append("filled-number")
                else:
                    classes.append("given-number")
                    
            class_str = f'class="{" ".join(classes)}"' if classes else ""
            html += f'<td {class_str}>{display_val}</td>'
        html += "</tr>"
    html += "</table></div>"
    return html

def run_web():
    st.set_page_config(page_title="Sudoku Solver", page_icon="🧩")
    
    # CSS ตกแต่งช่องกรอกตัวเลขไม่ให้ลายตา
    st.markdown("""
        <style>
            div[data-testid="column"] { padding: 1px !important; }
            .stNumberInput input { 
                text-align: center; 
                font-weight: bold; 
                font-size: 18px !important;
                border-radius: 4px;
            }
            .block-separator { margin-bottom: 8px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🧩 Sudoku Solver Algorithm")
    st.caption("โครงงานแก้ปัญหาตารางโซดุกุด้วย Backtracking & Constraint Satisfaction")

    input_mode = st.radio(
        "เลือกช่องทางการนำเข้าข้อมูล:",
        ["📂 อัปโหลดไฟล์ .txt", "🖼️ อัปโหลดรูปภาพโจทย์", "✍️ กรอกตัวเลขบนตารางเว็บ"],
        horizontal=True
    )

    board = None

    if input_mode == "📂 อัปโหลดไฟล์ .txt":
        uploaded_file = st.file_uploader("เลือกไฟล์โจทย์ .txt (ขนาด 9x9)", type=["txt"])
        if uploaded_file is not None:
            try:
                content = uploaded_file.read().decode("utf-8")
                board = parse_txt_content(content)
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")

    elif input_mode == "🖼️ อัปโหลดรูปภาพโจทย์":
        uploaded_img = st.file_uploader("อัปโหลดรูปภาพโซดุกุ (.png, .jpg, .jpeg)", type=["png", "jpg", "jpeg"])
        if uploaded_img is not None:
            try:
                with st.spinner("กำลังสแกนตัวเลขจากรูปภาพ..."):
                    board = parse_image_to_board(uploaded_img.read())
                st.success("สแกนรูปภาพสำเร็จ! โปรดตรวจสอบความถูกต้องด้านล่างก่อนคำนวณ")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการสแกนรูปภาพ: {e}")

    else:
        st.write("กรอกตัวเลข 1-9 ลงในช่อง (ใส่ 0 สำหรับช่องว่าง):")
        grid_input = []
        for r in range(9):
            cols = st.columns(9)
            row_vals = []
            for c in range(9):
                # ตกแต่งพื้นหลังสลับบล็อก 3x3 เพื่อลดความลายตา
                val = cols[c].number_input(
                    label=f"r{r}c{c}",
                    min_value=0, max_value=9, value=0, step=1,
                    key=f"cell_{r}_{c}", label_visibility="collapsed"
                )
                row_vals.append(val)
            grid_input.append(row_vals)
            if (r + 1) % 3 == 0 and r < 8:
                st.markdown('<div class="block-separator"></div>', unsafe_allow_html=True)
        
        if st.button("🧩 คำนวณแก้โจทย์", type="primary"):
            board = grid_input

    if board is not None:
        st.subheader("📋 ตารางข้อมูลนำเข้า (Input)")
        st.markdown(render_sudoku_html(board), unsafe_allow_html=True)

        status, result, details, orig_board = process_sudoku(board)

        st.subheader("🎯 ผลการประมวลผล (Output)")
        
        if status == "INITIAL_CONFLICT":
            st.error("❌ NO SOLUTION: โจทย์มีเงื่อนไขขัดแย้งกันเองตั้งแต่เริ่มต้น")
            for err in details: st.write(f"- {err}")

        elif status == "NO_SOLUTION":
            st.error("❌ NO SOLUTION: ไม่สามารถหาคำตอบที่ถูกต้องได้")
            for err in details: st.write(f"- {err}")

        elif status == "MULTIPLE_SOLUTIONS":
            st.warning("⚠️ MULTIPLE SOLUTIONS: โจทย์มีคำตอบได้มากกว่า 1 แบบ")
            for err in details: st.write(f"- {err}")

        elif status == "COMPLETED":
            st.info("ℹ️ ตารางนี้กรอกตัวเลขสมบูรณ์และถูกต้องอยู่แล้ว:")
            st.markdown(render_sudoku_html(result, orig_board), unsafe_allow_html=True)

        elif status == "SUCCESS":
            st.success("🎉 เติมตัวเลขสมบูรณ์ตามกติกา (ตัวเลขที่เติมใหม่แสดงด้วยสีน้ำเงิน):")
            st.markdown(render_sudoku_html(result, orig_board), unsafe_allow_html=True)

if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].endswith("app.py"):
        try:
            with open(sys.argv[1], 'r') as f:
                board = parse_txt_content(f.read())
            status, result, details, _ = process_sudoku(board)
            if status in ["INITIAL_CONFLICT", "NO_SOLUTION", "MULTIPLE_SOLUTIONS"]:
                print(status)
                for d in details: print(f"- {d}")
            elif status in ["SUCCESS", "COMPLETED"]:
                print("--- RESULT ---")
                for row in result: print(" ".join(map(str, row)))
        except Exception as e:
            print(f"Error: {e}")
    else:
        run_web()