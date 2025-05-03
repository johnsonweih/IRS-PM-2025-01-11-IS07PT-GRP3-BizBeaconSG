import React from "react";
import BotResponse from "./BotResponse";

const IntroSection = () => {
  return (
    <div id="introsection">
      <h1>
        Intelligent Business Location Advisor
        <BotResponse response=" - Your Strategic Business Partner" />
      </h1>
      <h2>
        A sophisticated AI-powered system that helps entrepreneurs and business owners
        make informed decisions about their business ventures. Whether you're starting
        a new business or expanding an existing one, our advisor provides comprehensive
        location and business strategy recommendations tailored to your specific needs.
      </h2>
      Features:
      <ul>
        <li>Personalized business type recommendations based on your interests and skills</li>
        <li>Strategic location analysis considering multiple crucial factors</li>
        <li>Market analysis and competition insights</li>
        <li>Cost and feasibility assessments</li>
        <li>Regulatory and zoning guidance</li>
        <li>Growth potential and economic indicator analysis</li>
      </ul>
      <p>
        Make data-driven decisions for your business with our intelligent advisor.
        Get detailed, well-reasoned recommendations that consider your unique situation,
        budget, and goals. Start your journey to business success today!
      </p>
    </div>
  );
};

export default IntroSection;
