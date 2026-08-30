import UIKit
import WebKit

@main
final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = ViewController()
        window.makeKeyAndVisible()

        self.window = window

        return true
    }
}

final class ViewController: UIViewController {
    private let counterLabel = UILabel()
    private var timer: Timer?
    private var tick = 0

    override func viewDidLoad() {
        super.viewDidLoad()

        view.backgroundColor = .systemBackground

        let titleLabel = UILabel()
        titleLabel.translatesAutoresizingMaskIntoConstraints = false
        titleLabel.text = "App title"
        titleLabel.font = .preferredFont(forTextStyle: .largeTitle)
        titleLabel.adjustsFontForContentSizeCategory = true
        titleLabel.accessibilityIdentifier = "app-title"

        let bodyLabel = UILabel()
        bodyLabel.translatesAutoresizingMaskIntoConstraints = false
        bodyLabel.text = "Release simulator fixture"
        bodyLabel.font = .preferredFont(forTextStyle: .body)
        bodyLabel.adjustsFontForContentSizeCategory = true

        let webView = WKWebView(frame: .zero)
        webView.translatesAutoresizingMaskIntoConstraints = false
        webView.accessibilityIdentifier = "web-content"
        webView.loadHTMLString(
            "<main><h1>Web content</h1><p>SpringBoard accessibility session fixture.</p></main>",
            baseURL: nil
        )

        let sheet = UIView()
        sheet.translatesAutoresizingMaskIntoConstraints = false
        sheet.backgroundColor = .secondarySystemBackground
        sheet.layer.cornerRadius = 16
        sheet.accessibilityIdentifier = "visible-sheet"

        let sheetTitle = UILabel()
        sheetTitle.translatesAutoresizingMaskIntoConstraints = false
        sheetTitle.text = "Visible sheet title"
        sheetTitle.font = .preferredFont(forTextStyle: .title2)
        sheetTitle.adjustsFontForContentSizeCategory = true
        sheetTitle.accessibilityIdentifier = "visible-sheet-title"

        counterLabel.translatesAutoresizingMaskIntoConstraints = false
        counterLabel.text = "Accessibility churn 0"
        counterLabel.font = .monospacedDigitSystemFont(ofSize: 15, weight: .regular)
        counterLabel.accessibilityIdentifier = "accessibility-churn"

        sheet.addSubview(sheetTitle)
        sheet.addSubview(counterLabel)

        view.addSubview(titleLabel)
        view.addSubview(bodyLabel)
        view.addSubview(webView)
        view.addSubview(sheet)

        let guide = view.safeAreaLayoutGuide

        NSLayoutConstraint.activate([
            titleLabel.topAnchor.constraint(equalTo: guide.topAnchor, constant: 28),
            titleLabel.leadingAnchor.constraint(equalTo: guide.leadingAnchor, constant: 24),
            titleLabel.trailingAnchor.constraint(equalTo: guide.trailingAnchor, constant: -24),

            bodyLabel.topAnchor.constraint(equalTo: titleLabel.bottomAnchor, constant: 12),
            bodyLabel.leadingAnchor.constraint(equalTo: titleLabel.leadingAnchor),
            bodyLabel.trailingAnchor.constraint(equalTo: titleLabel.trailingAnchor),

            webView.topAnchor.constraint(equalTo: bodyLabel.bottomAnchor, constant: 24),
            webView.leadingAnchor.constraint(equalTo: guide.leadingAnchor, constant: 24),
            webView.trailingAnchor.constraint(equalTo: guide.trailingAnchor, constant: -24),
            webView.bottomAnchor.constraint(equalTo: sheet.topAnchor, constant: -24),

            sheet.leadingAnchor.constraint(equalTo: guide.leadingAnchor, constant: 16),
            sheet.trailingAnchor.constraint(equalTo: guide.trailingAnchor, constant: -16),
            sheet.bottomAnchor.constraint(equalTo: guide.bottomAnchor, constant: -16),

            sheetTitle.topAnchor.constraint(equalTo: sheet.topAnchor, constant: 20),
            sheetTitle.leadingAnchor.constraint(equalTo: sheet.leadingAnchor, constant: 20),
            sheetTitle.trailingAnchor.constraint(equalTo: sheet.trailingAnchor, constant: -20),

            counterLabel.topAnchor.constraint(equalTo: sheetTitle.bottomAnchor, constant: 12),
            counterLabel.leadingAnchor.constraint(equalTo: sheetTitle.leadingAnchor),
            counterLabel.trailingAnchor.constraint(equalTo: sheetTitle.trailingAnchor),
            counterLabel.bottomAnchor.constraint(equalTo: sheet.bottomAnchor, constant: -20),
        ])
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)

        if timer == nil {
            timer = Timer.scheduledTimer(
                timeInterval: 0.25,
                target: self,
                selector: #selector(updateChurnLabel),
                userInfo: nil,
                repeats: true
            )
        }
    }

    @objc
    private func updateChurnLabel() {
        tick += 1
        counterLabel.text = "Accessibility churn \(tick)"
    }
}
