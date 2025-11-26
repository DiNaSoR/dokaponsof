"""
3D Model Viewer Widget using PyVista.
Provides an interactive 3D viewport for viewing game models.
"""

try:
    import pyvista as pv
    from pyvistaqt import QtInteractor
    PYVISTA_AVAILABLE = True
except ImportError:
    PYVISTA_AVAILABLE = False

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
import numpy as np


class Viewer3DWidget(QWidget):
    """
    A 3D model viewer widget that can display meshes.
    Falls back to a placeholder if PyVista is not available.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if PYVISTA_AVAILABLE:
            # Create PyVista Qt interactor
            self.frame = QFrame()
            frame_layout = QVBoxLayout(self.frame)
            frame_layout.setContentsMargins(0, 0, 0, 0)
            
            # Create the plotter
            self.plotter = QtInteractor(self.frame)
            self.plotter.set_background('#1e1e1e')  # Dark background
            self.plotter.add_axes()
            
            frame_layout.addWidget(self.plotter.interactor)
            layout.addWidget(self.frame)
            
            self._has_mesh = False
        else:
            # Fallback placeholder
            self.placeholder = QLabel("3D Viewer not available\n\nInstall pyvista and pyvistaqt:\npip install pyvista pyvistaqt")
            self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.placeholder.setStyleSheet("""
                QLabel {
                    background-color: #2d2d30;
                    color: #808080;
                    border-radius: 4px;
                    padding: 20px;
                }
            """)
            layout.addWidget(self.placeholder)
            self.plotter = None
    
    def display_mesh(self, vertices: np.ndarray, faces: np.ndarray = None, 
                     normals: np.ndarray = None, color: str = '#4a9eff'):
        """
        Display a 3D mesh.
        
        Args:
            vertices: Nx3 array of vertex positions
            faces: Optional Mx3 array of face indices (triangles)
            normals: Optional Nx3 array of vertex normals
            color: Mesh color
        """
        if not PYVISTA_AVAILABLE or self.plotter is None:
            return False
        
        try:
            self.plotter.clear()
            
            if faces is not None and len(faces) > 0:
                # Create proper faces array for PyVista (prepend 3 for triangles)
                pv_faces = np.hstack([
                    np.full((len(faces), 1), 3, dtype=np.int32),
                    faces.astype(np.int32)
                ]).ravel()
                
                mesh = pv.PolyData(vertices, pv_faces)
            else:
                # Point cloud if no faces
                mesh = pv.PolyData(vertices)
            
            if normals is not None and len(normals) == len(vertices):
                mesh.point_data['Normals'] = normals
            
            # Add the mesh with nice rendering
            self.plotter.add_mesh(
                mesh, 
                color=color,
                show_edges=True,
                edge_color='#303030',
                smooth_shading=True,
                opacity=1.0
            )
            
            # Reset camera to fit the model
            self.plotter.reset_camera()
            self.plotter.view_isometric()
            
            self._has_mesh = True
            return True
            
        except Exception as e:
            print(f"Error displaying mesh: {e}")
            return False
    
    def display_point_cloud(self, points: np.ndarray, colors: np.ndarray = None):
        """Display a point cloud."""
        if not PYVISTA_AVAILABLE or self.plotter is None:
            return False
        
        try:
            self.plotter.clear()
            
            cloud = pv.PolyData(points)
            
            if colors is not None:
                cloud.point_data['Colors'] = colors
                self.plotter.add_mesh(cloud, scalars='Colors', rgb=True, point_size=3)
            else:
                self.plotter.add_mesh(cloud, color='#4a9eff', point_size=3)
            
            self.plotter.reset_camera()
            self._has_mesh = True
            return True
            
        except Exception as e:
            print(f"Error displaying point cloud: {e}")
            return False
    
    def clear(self):
        """Clear the 3D view."""
        if PYVISTA_AVAILABLE and self.plotter is not None:
            self.plotter.clear()
            self._has_mesh = False
    
    def set_background(self, color: str):
        """Set the background color."""
        if PYVISTA_AVAILABLE and self.plotter is not None:
            self.plotter.set_background(color)
    
    def screenshot(self, filename: str = None):
        """Take a screenshot of the current view."""
        if PYVISTA_AVAILABLE and self.plotter is not None:
            return self.plotter.screenshot(filename)
        return None
    
    def closeEvent(self, event):
        """Clean up when closing."""
        if PYVISTA_AVAILABLE and self.plotter is not None:
            self.plotter.close()
        super().closeEvent(event)


def is_3d_viewer_available() -> bool:
    """Check if 3D viewer is available."""
    return PYVISTA_AVAILABLE

