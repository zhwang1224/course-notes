import random
import time

import matplotlib.pyplot as plt

class EightQueens:
    def __init__(self):
        # 初始化一个8x8的棋盘，每个皇后的位置由一个列数组 'board' 表示
        self.board = [random.randint(0, 7) for _ in range(8)]
    
    def calculate_conflicts(self, board):
        # 计算给定棋盘状态下的冲突数量
        conflicts = 0
        for i in range(len(board)):
            for j in range(i + 1, len(board)):
                if board[i] == board[j] or abs(board[i] - board[j]) == abs(i - j):  # 如果两个皇后在同一行或对角线上
                    conflicts += 1  # 冲突计数加一
        return conflicts

    def get_neighbors(self, board):
        # 通过将每个列中的皇后移动到不同的行来生成所有可能的状态
        neighbors = []
        for col in range(len(board)):
            for row in range(8):
                if board[col] != row:
                    neighbor = list(board)
                    neighbor[col] = row
                    neighbors.append(neighbor)
        return neighbors

    def hill_climb(self, board=None):
        # 爬山算法
        if board is None:
            board = self.board
        current_board = board
        current_conflicts = self.calculate_conflicts(current_board)

        while True:
            neighbors = self.get_neighbors(current_board)
            best_neighbor = None  # 最佳邻居
            best_neighbor_conflicts = float('inf')  # 初始化为无穷大

            for neighbor in neighbors:
                conflicts = self.calculate_conflicts(neighbor)
                if conflicts < best_neighbor_conflicts:
                    best_neighbor = neighbor
                    best_neighbor_conflicts = conflicts

            if best_neighbor_conflicts >= current_conflicts:
                break  # 没有更好的邻居了，停止爬山

            current_board = best_neighbor
            current_conflicts = best_neighbor_conflicts

        return current_board, current_conflicts

    def random_restart_hill_climb(self, max_restarts=100):
        # 随机重启爬山算法
        best_board = None
        best_conflicts = float('inf')
        
        for _ in range(max_restarts):
            board = [random.randint(0, 7) for _ in range(8)]
            solution, conflicts = self.hill_climb(board)
            if conflicts < best_conflicts:
                best_board = solution
                best_conflicts = conflicts
            if best_conflicts == 0:
                break
        
        return best_board, best_conflicts

    def local_beam_search(self, beam_width):
        # 局部束搜索
        current_boards = [[random.randint(0, 7) for _ in range(8)] for _ in range(beam_width)]
        current_conflicts = [self.calculate_conflicts(board) for board in current_boards]

        while True:
            all_neighbors = []
            for board in current_boards:
                all_neighbors.extend(self.get_neighbors(board))

            all_neighbors.sort(key=lambda board: self.calculate_conflicts(board))
            best_neighbors = all_neighbors[:beam_width]
            best_conflicts = [self.calculate_conflicts(board) for board in best_neighbors]

            if min(best_conflicts) == 0:
                return best_neighbors[best_conflicts.index(min(best_conflicts))], 0

            if best_conflicts == current_conflicts:
                break  # 没有更好的邻居了，停止束搜索

            current_boards = best_neighbors
            current_conflicts = best_conflicts

        return current_boards[0], current_conflicts[0]

    def stochastic_beam_search(self, beam_width):
        # 随机束搜索
        current_boards = [[random.randint(0, 7) for _ in range(8)] for _ in range(beam_width)]
        current_conflicts = [self.calculate_conflicts(board) for board in current_boards]

        while True:
            all_neighbors = []
            for board in current_boards:
                all_neighbors.extend(self.get_neighbors(board))

            all_neighbors.sort(key=lambda board: self.calculate_conflicts(board))
            best_neighbors = random.sample(all_neighbors, beam_width)
            best_conflicts = [self.calculate_conflicts(board) for board in best_neighbors]

            if min(best_conflicts) == 0:
                return best_neighbors[best_conflicts.index(min(best_conflicts))], 0

            if best_conflicts == current_conflicts:
                break  # 没有更好的邻居了，停止束搜索

            current_boards = best_neighbors
            current_conflicts = best_conflicts

        return current_boards[0], current_conflicts[0]

    def draw_board(self, board):
        # 画出八皇后棋盘
        fig, ax = plt.subplots()
        # 画棋盘
        for i in range(8):
            for j in range(8):
                if (i + j) % 2 == 0:
                    ax.add_patch(plt.Rectangle((i, j), 1, 1, color='white'))
                else:
                    ax.add_patch(plt.Rectangle((i, j), 1, 1, color='gray'))
        # 画皇后
        for col in range(len(board)):
            row = board[col]
            ax.text(col + 0.5, row + 0.5, '♛', ha='center', va='center', fontsize=30, color='black')

        ax.set_xlim(0, 8)
        ax.set_ylim(0, 8)
        ax.set_xticks([])
        ax.set_yticks([])
        plt.gca().invert_yaxis()
        plt.show()

    def evaluate_local_beam_search(self, beam_widths, iterations=50):
        times = []
        success_counts = []

        for beam_width in beam_widths:
            total_time = 0
            success_count = 0
            for _ in range(iterations):
                start_time = time.time()
                solution, conflicts = self.local_beam_search(beam_width)
                end_time = time.time()
                total_time += (end_time - start_time)
                if conflicts == 0:
                    success_count += 1
            times.append(total_time / iterations)
            success_counts.append(success_count)

        return times, success_counts

    def evaluate_stochastic_beam_search(self, beam_widths, iterations=50):
        times = []
        success_counts = []

        for beam_width in beam_widths:
            total_time = 0
            success_count = 0
            for _ in range(iterations):
                start_time = time.time()
                solution, conflicts = self.stochastic_beam_search(beam_width)
                end_time = time.time()
                total_time += (end_time - start_time)
                if conflicts == 0:
                    success_count += 1
            times.append(total_time / iterations)
            success_counts.append(success_count)

        return times, success_counts

# 主程序
if __name__ == "__main__":
    solver = EightQueens()
    print("Initial board:", solver.board)

    # 评估局部束搜索算法
    beam_widths = [5,10,20,30,40,50]
    times_beam, success_counts_beam = solver.evaluate_local_beam_search(beam_widths, iterations=5)

    # 评估随机束搜索算法
    times_stochastic, success_counts_stochastic = solver.evaluate_stochastic_beam_search(beam_widths, iterations=5)

    # 绘制图表
    plt.figure(figsize=(16, 6))

    # 求解时间图表
    plt.subplot(1, 2, 1)
    plt.plot(beam_widths, times_beam, marker='o', label='Local Beam Search')
    plt.plot(beam_widths, times_stochastic, marker='s', label='Stochastic Beam Search')
    plt.title('Average Solving Time vs Beam Width')
    plt.xlabel('Beam Width')
    plt.ylabel('Average Solving Time (seconds)')
    plt.legend()

    # 成功次数图表
    plt.subplot(1, 2, 2)
    plt.plot(beam_widths, success_counts_beam, marker='o', label='Local Beam Search')
    plt.plot(beam_widths, success_counts_stochastic, marker='s', label='Stochastic Beam Search')
    plt.title('Success Count vs Beam Width')
    plt.xlabel('Beam Width')
    plt.ylabel('Success Count out of 50')
    plt.legend()

    plt.tight_layout()
    plt.show()
