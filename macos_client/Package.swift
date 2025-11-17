// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ManagedNebula",
    platforms: [
        .macOS(.v12)
    ],
    products: [
        .executable(
            name: "ManagedNebula",
            targets: ["ManagedNebula"]
        )
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "ManagedNebula",
            dependencies: [],
            path: "ManagedNebula/Sources"
        )
    ]
)
