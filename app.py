import sys
import copy
import streamlit as st

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

def is_valid(board, row, col, num):
    """ตรวจสอบเงื่อนไขความถูกต้อง (Constraint Satisfaction)"""
    for i in range(9):
        if board[row][i] == num or board[i][col] == num:
            return False
    start_row, start_col = 3 * (row // 3), 3 * (col // 3)
    for i in range(3):
        for j in range(3):
            if board[start_row + i][start_col + j] == num:
                return False
    return True

def check_initial_conflicts(board):
    """ตรวจสอบว่าโจทย์ที่ให้มามีตัวเลขขัดแย้งกันเองตั้งแต่ต้นหรือไม่"""
    for r in range(9):
        for c in range(9):
            if board[r][c] != 0:
                temp = board[r][c]
                board[r][c] = 0
                if not is_valid(board, r, c, temp):
                    board[r][c] = temp
                    return True
                board[r][c] = temp
    return False

def find_empty(board):
    """ค้นหาตำแหน่งช่องว่าง (เลข 0)"""
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return r, c
    return None

def solve_and_count(board, solutions):
    """อัลกอริทึม Backtracking สำหรับค้นหาและนับจำนวนคำตอบ"""
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
    """ฟังก์ชันหลักในการตรวจสอบและแยกกรณีพิเศษทั้งหมด"""
    if check_initial_conflicts(board):
        return "NO SOLUTION", None

    if find_empty(board) is None:
        return "COMPLETED", board

    solutions = []
    solve_and_count(board, solutions)

    if len(solutions) == 0:
        return "NO SOLUTION", None
    elif len(solutions) == 1:
        return "SUCCESS", solutions[0]
    else:
        return "MULTIPLE SOLUTIONS", None

def render_sudoku_html(board):
    """สร้าง HTML Table แบบปรับแต่ง CSS สำหรับแสดงผลตารางซูโดกุ"""
    html = """
    <style>
        .sudoku-container {
            display: flex;
            justify-content: center;
            margin: 15px 0;
        }
        .sudoku-table {
            border-collapse: collapse;
            border: 3px solid #111111;
            background-color: #ffffff;
            user-select: none;
        }
        .sudoku-table td {
            width: 42px;
            height: 42px;
            text-align: center;
            vertical-align: middle;
            font-size: 20px;
            font-weight: bold;
            color: #111111;
            border: 1px solid #b0b0b0;
        }
        .border-right-thick { border-right: 3px solid #111111 !important; }
        .border-bottom-thick { border-bottom: 3px solid #111111 !important; }
        .empty-cell { color: transparent; }
    </style>
    <div class="sudoku-container">
        <table class="sudoku-table">
    """
    for r in range(9):
        html += "<tr>"
        for c in range(9):
            classes = []
            if (c + 1) % 3 == 0 and c < 8:
                classes.append("border-right-thick")
            if (r + 1) % 3 == 0 and r < 8:
                classes.append("border-bottom-thick")
            
            val = board[r][c]
            if val == 0:
                classes.append("empty-cell")
                display_val = "0"
            else:
                display_val = str(val)
                
            class_str = f'class="{" ".join(classes)}"' if classes else ""
            html += f'<td {class_str}>{display_val}</td>'
        html += "</tr>"
    html += "</table></div>"
    return html

# --- ส่วนการแสดงผล WEB INTERFACE (Streamlit) ---
def run_web():
    st.set_page_config(page_title="Sudoku Solver", page_icon="🧩")
    st.title("🧩 Sudoku Solver Algorithm")
    st.caption("โครงงานแก้ปัญหาตารางโซดุกุด้วย Backtracking & Constraint Satisfaction")

    uploaded_file = st.file_uploader("อัปโหลดไฟล์โจทย์ .txt (ขนาด 9x9)", type=["txt"])

    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode("utf-8")
            board = parse_txt_content(content)
            
            st.subheader("📋 ตารางข้อมูลนำเข้า (Input)")
            st.markdown(render_sudoku_html(board), unsafe_allow_html=True)

            status, result = process_sudoku(board)

            st.subheader("🎯 ผลการประมวลผล (Output)")
            if status == "NO SOLUTION":
                st.error("❌ NO SOLUTION (โจทย์ขัดแย้งกันเองหรือไม่มีคำตอบที่ถูกต้อง)")
            elif status == "MULTIPLE SOLUTIONS":
                st.warning("⚠️ MULTIPLE SOLUTIONS (โจทย์มีคำตอบได้มากกว่า 1 แบบ)")
            elif status == "COMPLETED":
                st.info("ℹ️ ตารางนี้กรอกสมบูรณ์และถูกต้องอยู่แล้ว:")
                st.markdown(render_sudoku_html(result), unsafe_allow_html=True)
            elif status == "SUCCESS":
                st.success("🎉 เติมตัวเลขสมบูรณ์ตามกติกา:")
                st.markdown(render_sudoku_html(result), unsafe_allow_html=True)

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].endswith("app.py"):
        try:
            with open(sys.argv[1], 'r') as f:
                board = parse_txt_content(f.read())
            status, result = process_sudoku(board)
            if status in ["NO SOLUTION", "MULTIPLE SOLUTIONS"]:
                print(status)
            elif status in ["SUCCESS", "COMPLETED"]:
                print("--- RESULT ---")
                for row in result:
                    print(" ".join(map(str, row)))
        except Exception as e:
            print(f"Error: {e}")
    else:
        run_web()