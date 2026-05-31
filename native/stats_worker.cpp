#include <algorithm>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {

struct Entry {
    std::int64_t peer_id;
    std::uint64_t count;
};

auto escape_json(const std::string& value) -> std::string {
    std::string out;
    out.reserve(value.size());

    for (unsigned char ch : value) {
        switch (ch) {
            case '\\':
                out += "\\\\";
                break;
            case '"':
                out += "\\\"";
                break;
            case '\b':
                out += "\\b";
                break;
            case '\f':
                out += "\\f";
                break;
            case '\n':
                out += "\\n";
                break;
            case '\r':
                out += "\\r";
                break;
            case '\t':
                out += "\\t";
                break;
            default:
                if (ch < 0x20) {
                    static const char* hex = "0123456789abcdef";
                    out += "\\u00";
                    out += hex[(ch >> 4) & 0x0F];
                    out += hex[ch & 0x0F];
                } else {
                    out.push_back(static_cast<char>(ch));
                }
                break;
        }
    }

    return out;
}

}  // namespace

int main(int argc, char** argv) {
    std::size_t top_n = 10;
    if (argc > 1) {
        try {
            const auto parsed = std::stoull(argv[1]);
            if (parsed > 0) {
                top_n = parsed;
            }
        } catch (...) {
        }
    }

    std::unordered_map<std::int64_t, std::uint64_t> counts;
    std::string line;
    std::uint64_t total_messages = 0;

    while (std::getline(std::cin, line)) {
        if (line.empty()) {
            continue;
        }

        std::int64_t peer_id = 0;
        try {
            peer_id = std::stoll(line);
        } catch (...) {
            continue;
        }

        ++counts[peer_id];
        ++total_messages;
    }

    std::vector<Entry> ranked;
    ranked.reserve(counts.size());
    for (const auto& [peer_id, count] : counts) {
        ranked.push_back(Entry{peer_id, count});
    }

    std::sort(
        ranked.begin(),
        ranked.end(),
        [](const Entry& left, const Entry& right) {
            if (left.count != right.count) {
                return left.count > right.count;
            }
            return left.peer_id < right.peer_id;
        }
    );

    std::ostringstream out;
    out << "{\"total_messages\":" << total_messages
        << ",\"unique_authors\":" << counts.size()
        << ",\"top\":[";

    const auto top_size = std::min(top_n, ranked.size());
    for (std::size_t i = 0; i < top_size; ++i) {
        if (i > 0) {
            out << ',';
        }
        out << "{\"peer_id\":" << ranked[i].peer_id
            << ",\"count\":" << ranked[i].count << '}';
    }

    out << "],\"all\":[";

    for (std::size_t i = 0; i < ranked.size(); ++i) {
        if (i > 0) {
            out << ',';
        }
        out << "{\"peer_id\":" << ranked[i].peer_id
            << ",\"count\":" << ranked[i].count << '}';
    }

    out << "]}";
    std::cout << out.str();
    return 0;
}
