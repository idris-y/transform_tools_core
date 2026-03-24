# Transform Tools Core for Blender
> **Advanced gizmo control & precision transformations for Blender.**

The **Transform Tools** addon enhances object and mesh manipulation by utilizing a unique dual-gizmo system, providing unprecedented precision over transformations. 

The core workflow involves defining a **'Previous'** (start) and an **'Active'** (end) gizmo state, allowing you to seamlessly apply complex movements, rotations, and scales to elements between these two defined states.

---

## ✨ Key Features

* **Dual-Gizmo Transformations:** Precisely transform objects or mesh components from one exact state to another.
* **Custom Orientation ('Cursor Pivot'):** Use the Active gizmo as a temporary, highly accurate custom transform orientation for Blender's native tools.
* **Standard Redo Panel Support:** After any operation, use Blender's native **'Adjust Last Operation'** panel (bottom-left of the viewport, or press `F9`) to interactively tweak your transformation.
* **Complex Duplication & Instances:** Safely duplicate or instance complex objects (including boolean setups and modifiers) during transformations.
* **Mesh Extrusion:** Seamlessly extrude mesh components directly along your custom gizmo paths in Edit Mode.

---

## 📥 Installation

*Note: Transform Tools Core requires **Blender 4.2.0** or newer.*

1. Download the latest release `.zip` file from the **[Releases page](../../releases)**. *(Do not download the raw source code).*
2. Open Blender and go to **Edit > Preferences**.
3. Navigate to the **Get Extensions** (or Add-ons) tab.
4. Click the drop-down arrow at the top right and select **Install from Disk...**
5. Select the downloaded `.zip` file.
6. Enable the extension by checking the box next to "Transform Tools Core".

---

## 🚀 Getting Started

### 1. Find the Panel
The main operations panel is located in the **3D Viewport's Sidebar**. 
Press `N` in the 3D viewport to open the sidebar, and look for the **TTools C** tab.

### 2. Basic Workflow
1. **Create Previous:** Define the 'Previous' gizmo to establish your starting state.
2. **Create Active:** Define the 'Active' gizmo to establish your ending state.
3. **Select:** Select the object(s), vertices, edges, or faces you want to modify.
4. **Transform:** Click the **Transform** button in the TTools panel to apply the operation.
5. **Adjust:** Use the native **Adjust Last Operation** panel immediately after to tweak duplication, extrusion, scale, and flipping options.

---

## 📖 Documentation & Support

For a complete guide to ALL features and detailed explanations of every operator and setting, please visit the official documentation:

👉 **[Read the Full Documentation Here](https://idris-y.github.io/transform-tools-docs/core/)**

If you encounter any bugs or have feature requests, please open an issue on our GitHub tracker:
🐛 **[Report a Bug / Issue](https://github.com/idris-y/transform-tools/issues)**

---

**Author:** Yasser Idris  
**License:** GPL-3.0-or-later  
*Copyright © 2026 Yasser Idris*