import React from "react";
import NavLinks from "./NavLink";

const NavLinksContainer = ({ chatLog, setChatLog }) => {
  return (
    <div className="navLinks" style={{ position: "absolute", bottom: "10px" }}>
      {chatLog.length > 0 && (
        <NavLinks
          svg={
            <svg
              fill="#fff"
              viewBox="0 0 24 24"
              data-name="Flat Line"
              xmlns="http://www.w3.org/2000/svg"
              className="icon flat-line"
              stroke="#fff"
              width={23}
              height={23}
            >
              <path
                d="M5 8h13a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H5V8Z"
                transform="rotate(90 12 14)"
                style={{
                  fill: "#fff202022",
                  strokeWidth: 2,
                }}
              />
              <path
                d="M16 7V4a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3"
                style={{
                  fill: "none",
                  stroke: "#fff202022000000",
                  strokeLinecap: "round",
                  strokeLinejoin: "round",
                  strokeWidth: 2,
                }}
              />
              <path
                data-name="primary"
                d="M10 11v6m4-6v6M4 7h16m-2 13V7H6v13a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1Z"
                style={{
                  fill: "none",
                  stroke: "#fff202022000000",
                  strokeLinecap: "round",
                  strokeLinejoin: "round",
                  strokeWidth: 2,
                }}
              />
            </svg>
          }
          text="Clear Conversations"
          setChatLog={setChatLog}
        />
      )}
      <NavLinks
        svg={
          <svg
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            width={25}
            height={25}
          >
            <path
              stroke="#fff"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 6H7a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-5m-6 0 7.5-7.5M15 3h6v6"
            />
          </svg>
        }
        text="Updates & FAQ"
        link="https://help.openai.com/en/collections/3742473-chatgpt"
      />
    </div>
  );
};

export default NavLinksContainer;
