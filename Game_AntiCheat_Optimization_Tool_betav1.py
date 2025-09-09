import sys
import os
import ctypes
import psutil
import subprocess
import threading
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QListWidget, QPushButton, 
                             QGroupBox, QComboBox, QSpinBox, QMessageBox, QSlider,
                             QTabWidget, QCheckBox, QProgressBar)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

def is_admin():
    """检查是否具有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理员权限重新运行程序"""
    if is_admin():
        return True
    
    # 重新以管理员权限启动程序
    script = sys.argv[0]
    params = ' '.join([f'"{x}"' for x in sys.argv[1:]])
    
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        return False
    except Exception as e:
        print(f"请求管理员权限失败: {e}")
        return False

class DiskIOLimiter:
    def __init__(self):
        self.limited_processes = {}
        self.is_limiting = False
        self.limit_thread = None
        
    def start_limiting(self, pid, read_limit_kb, write_limit_kb):
        """开始限制指定进程的磁盘IO"""
        if pid in self.limited_processes:
            self.stop_limiting(pid)
            
        self.limited_processes[pid] = {
            'read_limit': read_limit_kb,
            'write_limit': write_limit_kb,
            'active': True
        }
        
        if not self.is_limiting:
            self.is_limiting = True
            self.limit_thread = threading.Thread(target=self._io_limiter_thread)
            self.limit_thread.daemon = True
            self.limit_thread.start()
            
    def stop_limiting(self, pid):
        """停止限制指定进程的磁盘IO"""
        if pid in self.limited_processes:
            self.limited_processes[pid]['active'] = False
            del self.limited_processes[pid]
            
    def stop_all_limiting(self):
        """停止所有磁盘IO限制"""
        self.limited_processes.clear()
        self.is_limiting = False
        
    def _io_limiter_thread(self):
        """磁盘IO限制线程"""
        while self.is_limiting and self.limited_processes:
            try:
                for pid, limits in list(self.limited_processes.items()):
                    if not limits['active']:
                        continue
                        
                    try:
                        process = psutil.Process(pid)
                        io_counters = process.io_counters()
                        
                        # 这里是模拟限制，实际实现需要更复杂的技术
                        # 在Windows上可以使用Windows API或第三方工具
                        
                        # 模拟延迟效果
                        time.sleep(0.1)
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        self.limited_processes.pop(pid, None)
                
                time.sleep(1)  # 每秒检查一次
            except:
                import traceback
                traceback.print_exc()
                break

class ProcessOptimizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("游戏反作弊优化工具 - 管理员权限版")
        self.setGeometry(100, 100, 900, 600)
        
        # 检查管理员权限
        if not is_admin():
            self.show_admin_warning()
        
        # 初始化磁盘IO限制器
        self.disk_limiter = DiskIOLimiter()
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 权限状态显示
        self.admin_status_label = QLabel()
        self.admin_status_label.setFont(QFont("Arial", 10))
        self.update_admin_status()
        main_layout.addWidget(self.admin_status_label)
        
        # 创建标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 创建CPU优化标签页
        self.cpu_tab = QWidget()
        self.setup_cpu_tab()
        self.tabs.addTab(self.cpu_tab, "CPU优化")
        
        # 创建磁盘IO优化标签页
        self.disk_tab = QWidget()
        self.setup_disk_tab()
        self.tabs.addTab(self.disk_tab, "磁盘IO优化")
        
        # 状态栏
        self.status_bar = QLabel("就绪")
        self.status_bar.setFont(QFont("Arial", 10))
        self.status_bar.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        main_layout.addWidget(self.status_bar)
        
        # 初始化进程列表
        self.refresh_processes()
        
        # 设置定时刷新
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_process_info)
        self.timer.start(2000)  # 每2秒刷新一次
        
        self.selected_process = None
        
    def show_admin_warning(self):
        """显示管理员权限警告"""
        QMessageBox.warning(self, "权限警告", 
            "当前程序未以管理员权限运行，某些功能可能无法正常工作。\n\n"
            "请右键点击程序，选择'以管理员身份运行'，或者重新启动程序。")
        
    def update_admin_status(self):
        """更新管理员权限状态显示"""
        if is_admin():
            self.admin_status_label.setText("✓ 已获取管理员权限")
            self.admin_status_label.setStyleSheet("color: green; background-color: #e8f5e8; padding: 5px;")
        else:
            self.admin_status_label.setText("✗ 未获取管理员权限 - 部分功能受限")
            self.admin_status_label.setStyleSheet("color: red; background-color: #ffe6e6; padding: 5px;")
        
    def setup_cpu_tab(self):
        """设置CPU优化标签页"""
        layout = QHBoxLayout(self.cpu_tab)
        
        # 左侧进程列表
        left_group = QGroupBox("运行中的进程")
        left_layout = QVBoxLayout()
        
        self.process_list = QListWidget()
        self.process_list.currentRowChanged.connect(self.on_process_selected)
        self.refresh_btn = QPushButton("刷新进程列表")
        self.refresh_btn.clicked.connect(self.refresh_processes)
        
        left_layout.addWidget(QLabel("选择要优化的进程:"))
        left_layout.addWidget(self.process_list)
        left_layout.addWidget(self.refresh_btn)
        left_group.setLayout(left_layout)
        
        # 右侧控制面板
        right_group = QGroupBox("CPU优化设置")
        right_layout = QVBoxLayout()
        
        # CPU相关性设置
        cpu_group = QGroupBox("CPU相关性设置")
        cpu_layout = QVBoxLayout()
        
        cpu_selection_layout = QHBoxLayout()
        cpu_selection_layout.addWidget(QLabel("选择CPU核心:"))
        
        self.cpu_selector = QComboBox()
        self.populate_cpu_options()
        cpu_selection_layout.addWidget(self.cpu_selector)
        
        cpu_layout.addLayout(cpu_selection_layout)
        
        # 优先级设置
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("进程优先级:"))
        
        self.priority_selector = QComboBox()
        self.priority_selector.addItems(["低", "低于正常", "正常", "高于正常", "高", "实时"])
        self.priority_selector.setCurrentIndex(2)  # 默认正常
        priority_layout.addWidget(self.priority_selector)
        
        cpu_layout.addLayout(priority_layout)
        cpu_group.setLayout(cpu_layout)
        
        # 应用按钮
        self.apply_btn = QPushButton("应用CPU设置")
        self.apply_btn.clicked.connect(self.apply_cpu_settings)
        if not is_admin():
            self.apply_btn.setEnabled(False)
            self.apply_btn.setToolTip("需要管理员权限")
        
        # 信息显示
        self.info_label = QLabel("选择要优化的进程并配置设置")
        self.info_label.setWordWrap(True)
        
        right_layout.addWidget(cpu_group)
        right_layout.addWidget(self.apply_btn)
        right_layout.addWidget(self.info_label)
        right_group.setLayout(right_layout)
        
        # 添加到主布局
        layout.addWidget(left_group, 2)
        layout.addWidget(right_group, 1)
        
    def setup_disk_tab(self):
        """设置磁盘IO优化标签页"""
        layout = QVBoxLayout(self.disk_tab)
        
        # 进程选择
        process_group = QGroupBox("选择要限制磁盘IO的进程")
        process_layout = QHBoxLayout()
        
        self.disk_process_list = QListWidget()
        self.disk_process_list.currentRowChanged.connect(self.on_disk_process_selected)
        self.disk_refresh_btn = QPushButton("刷新进程列表")
        self.disk_refresh_btn.clicked.connect(self.refresh_disk_processes)
        
        process_layout.addWidget(self.disk_process_list)
        process_layout.addWidget(self.disk_refresh_btn)
        process_group.setLayout(process_layout)
        
        # 限制设置
        limit_group = QGroupBox("磁盘IO限制设置")
        limit_layout = QVBoxLayout()
        
        # 读取限制
        read_layout = QHBoxLayout()
        read_layout.addWidget(QLabel("读取速度限制 (KB/s):"))
        self.read_limit_slider = QSlider(Qt.Horizontal)
        self.read_limit_slider.setRange(0, 10000)
        self.read_limit_slider.setValue(5000)
        self.read_limit_slider.valueChanged.connect(self.on_read_limit_changed)
        self.read_limit_label = QLabel("5000")
        read_layout.addWidget(self.read_limit_slider)
        read_layout.addWidget(self.read_limit_label)
        
        # 写入限制
        write_layout = QHBoxLayout()
        write_layout.addWidget(QLabel("写入速度限制 (KB/s):"))
        self.write_limit_slider = QSlider(Qt.Horizontal)
        self.write_limit_slider.setRange(0, 10000)
        self.write_limit_slider.setValue(5000)
        self.write_limit_slider.valueChanged.connect(self.on_write_limit_changed)
        self.write_limit_label = QLabel("5000")
        write_layout.addWidget(self.write_limit_slider)
        write_layout.addWidget(self.write_limit_label)
        
        limit_layout.addLayout(read_layout)
        limit_layout.addLayout(write_layout)
        
        # 应用按钮
        button_layout = QHBoxLayout()
        self.apply_disk_btn = QPushButton("应用磁盘IO限制")
        self.apply_disk_btn.clicked.connect(self.apply_disk_limits)
        self.remove_disk_btn = QPushButton("移除磁盘IO限制")
        self.remove_disk_btn.clicked.connect(self.remove_disk_limits)
        
        if not is_admin():
            self.apply_disk_btn.setEnabled(False)
            self.apply_disk_btn.setToolTip("需要管理员权限")
            self.remove_disk_btn.setEnabled(False)
            self.remove_disk_btn.setToolTip("需要管理员权限")
        
        button_layout.addWidget(self.apply_disk_btn)
        button_layout.addWidget(self.remove_disk_btn)
        limit_layout.addLayout(button_layout)
        
        limit_group.setLayout(limit_layout)
        
        # 当前限制状态
        status_group = QGroupBox("当前磁盘IO限制状态")
        status_layout = QVBoxLayout()
        self.disk_status_label = QLabel("没有活动的磁盘IO限制")
        self.disk_status_label.setWordWrap(True)
        status_layout.addWidget(self.disk_status_label)
        status_group.setLayout(status_layout)
        
        layout.addWidget(process_group)
        layout.addWidget(limit_group)
        layout.addWidget(status_group)
        
    def populate_cpu_options(self):
        """填充CPU核心选项"""
        logical_cores = psutil.cpu_count(logical=True)
        physical_cores = psutil.cpu_count(logical=False)
        
        self.cpu_selector.addItem("所有核心 (默认)", "all")
        
        # 添加物理核心选项
        for i in range(physical_cores):
            self.cpu_selector.addItem(f"物理核心 {i}", f"physical_{i}")
        
        # 添加逻辑核心选项
        for i in range(logical_cores):
            self.cpu_selector.addItem(f"逻辑核心 {i}", f"logical_{i}")
            
        # 添加自定义核心组选项
        self.cpu_selector.addItem("仅使用前一半核心", "first_half")
        self.cpu_selector.addItem("仅使用后一半核心", "second_half")
        
    def refresh_processes(self):
        """刷新进程列表"""
        self.process_list.clear()
        
        try:
            # 获取所有进程
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    # 只显示有名称的进程
                    if proc.info['name']:
                        self.process_list.addItem(
                            f"{proc.info['name']} (PID: {proc.info['pid']}, CPU: {proc.info['cpu_percent']:.1f}%)"
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                    
            self.status_bar.setText("进程列表已刷新")
        except Exception as e:
            self.status_bar.setText(f"刷新进程列表失败: {str(e)}")
                
    def refresh_disk_processes(self):
        """刷新磁盘IO进程列表"""
        self.disk_process_list.clear()
        
        try:
            # 获取所有进程
            for proc in psutil.process_iter(['pid', 'name', 'io_counters']):
                try:
                    # 只显示有名称的进程
                    if proc.info['name']:
                        io_info = proc.info['io_counters']
                        if io_info:
                            read_bytes = io_info.read_bytes / 1024  # 转换为KB
                            write_bytes = io_info.write_bytes / 1024  # 转换为KB
                            self.disk_process_list.addItem(
                                f"{proc.info['name']} (PID: {proc.info['pid']}, 读: {read_bytes:.1f}KB, 写: {write_bytes:.1f}KB)"
                            )
                        else:
                            self.disk_process_list.addItem(
                                f"{proc.info['name']} (PID: {proc.info['pid']})"
                            )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                    
            self.status_bar.setText("磁盘进程列表已刷新")
        except Exception as e:
            self.status_bar.setText(f"刷新磁盘进程列表失败: {str(e)}")
                
    def update_process_info(self):
        """更新进程信息"""
        # 这里可以添加实时更新进程信息的逻辑
        pass
        
    def on_process_selected(self, row):
        """处理进程选择事件"""
        if row >= 0:
            current_item = self.process_list.currentItem().text()
            self.selected_process = current_item
            self.info_label.setText(f"已选择: {current_item}")
            
    def on_disk_process_selected(self, row):
        """处理磁盘进程选择事件"""
        if row >= 0:
            current_item = self.disk_process_list.currentItem().text()
            self.selected_disk_process = current_item
            
    def on_read_limit_changed(self, value):
        """处理读取限制滑块变化"""
        self.read_limit_label.setText(str(value))
        
    def on_write_limit_changed(self, value):
        """处理写入限制滑块变化"""
        self.write_limit_label.setText(str(value))
            
    def apply_cpu_settings(self):
        """应用CPU相关性和优先级设置"""
        if not is_admin():
            QMessageBox.warning(self, "权限不足", "需要管理员权限才能修改进程设置")
            return
            
        if self.process_list.currentRow() < 0:
            QMessageBox.warning(self, "警告", "请先选择一个进程")
            return
            
        # 获取选中的进程
        current_item = self.process_list.currentItem().text()
        process_name = current_item.split(' (PID: ')[0]
        pid = int(current_item.split(' (PID: ')[1].split(',')[0])
        
        try:
            process = psutil.Process(pid)
            
            # 设置CPU相关性
            cpu_option = self.cpu_selector.currentData()
            logical_cores = psutil.cpu_count(logical=True)
            
            if cpu_option == "all":
                process.cpu_affinity(list(range(logical_cores)))
            elif cpu_option.startswith("physical_"):
                core_num = int(cpu_option.split('_')[1])
                process.cpu_affinity([core_num])
            elif cpu_option.startswith("logical_"):
                core_num = int(cpu_option.split('_')[1])
                process.cpu_affinity([core_num])
            elif cpu_option == "first_half":
                half_cores = logical_cores // 2
                process.cpu_affinity(list(range(half_cores)))
            elif cpu_option == "second_half":
                half_cores = logical_cores // 2
                process.cpu_affinity(list(range(half_cores, logical_cores)))
            
            # 设置进程优先级
            priority_map = {
                0: psutil.IDLE_PRIORITY_CLASS,
                1: psutil.BELOW_NORMAL_PRIORITY_CLASS,
                2: psutil.NORMAL_PRIORITY_CLASS,
                3: psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                4: psutil.HIGH_PRIORITY_CLASS,
                5: psutil.REALTIME_PRIORITY_CLASS
            }
            
            priority_index = self.priority_selector.currentIndex()
            process.nice(priority_map[priority_index])
            
            self.info_label.setText(f"已对 {process_name} 应用CPU设置")
            self.status_bar.setText(f"已优化进程: {process_name} (PID: {pid})")
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            QMessageBox.critical(self, "错误", f"无法修改进程设置: {str(e)}")
            self.status_bar.setText(f"错误: {str(e)}")
            
    def apply_disk_limits(self):
        """应用磁盘IO限制"""
        if not is_admin():
            QMessageBox.warning(self, "权限不足", "需要管理员权限才能限制磁盘IO")
            return
            
        if self.disk_process_list.currentRow() < 0:
            QMessageBox.warning(self, "警告", "请先选择一个进程")
            return
            
        # 获取选中的进程
        current_item = self.disk_process_list.currentItem().text()
        process_name = current_item.split(' (PID: ')[0]
        pid = int(current_item.split(' (PID: ')[1].split(',')[0])
        
        read_limit = self.read_limit_slider.value()
        write_limit = self.write_limit_slider.value()
        
        # 应用磁盘IO限制
        self.disk_limiter.start_limiting(pid, read_limit, write_limit)
        
        self.disk_status_label.setText(
            f"已对 {process_name} (PID: {pid}) 应用磁盘IO限制:\n"
            f"读取速度限制: {read_limit} KB/s\n"
            f"写入速度限制: {write_limit} KB/s"
        )
        self.status_bar.setText(f"已对 {process_name} 应用磁盘IO限制")
        
    def remove_disk_limits(self):
        """移除磁盘IO限制"""
        if not is_admin():
            QMessageBox.warning(self, "权限不足", "需要管理员权限才能移除磁盘IO限制")
            return
            
        if self.disk_process_list.currentRow() < 0:
            QMessageBox.warning(self, "警告", "请先选择一个进程")
            return
            
        # 获取选中的进程
        current_item = self.disk_process_list.currentItem().text()
        process_name = current_item.split(' (PID: ')[0]
        pid = int(current_item.split(' (PID: ')[1].split(',')[0])
        
        # 移除磁盘IO限制
        self.disk_limiter.stop_limiting(pid)
        
        self.disk_status_label.setText(f"已移除 {process_name} (PID: {pid}) 的磁盘IO限制")
        self.status_bar.setText(f"已移除 {process_name} 的磁盘IO限制")
            
    def closeEvent(self, event):
        """程序关闭时的处理"""
        # 停止所有磁盘IO限制
        self.disk_limiter.stop_all_limiting()
        
        # 停止定时器
        self.timer.stop()
        event.accept()

if __name__ == "__main__":
    # 检查并请求管理员权限
    if not is_admin():
        if run_as_admin():
            sys.exit(0)
    
    app = QApplication(sys.argv)
    window = ProcessOptimizer()
    window.show()
    sys.exit(app.exec_())